# IAM-IQ server bundle

Everything needed to run IAM-IQ on a Linux server that has Docker: the app, the 13 RefMap/ImAFUSA backends, MinIO
with the real partner data, and a private Kubernetes cluster (minikube) to run them in. No sudo and no internet
access for our images are needed; minikube downloads its own Kubernetes images on the first start.

## Requirements

- Linux x86-64 with Docker, and your user in the `docker` group
- About 12 GB free where Docker stores images (`docker info -f '{{.DockerRootDir}}'`) and 10 GB where this folder lives
- Defaults: 6 CPUs and 16 GB RAM for the cluster (`IAMIQ_CPUS`, `IAMIQ_MEMORY`, `IAMIQ_DISK` to change)

## Install

```bash
rsync -a --partial --info=progress2 ~/iam-iq-bundle/ USER@SERVER:/path/with/space/iam-iq-bundle/   # from your machine
ssh USER@SERVER
cd /path/with/space/iam-iq-bundle && ./install.sh
```

`install.sh` checks the files (SHA256SUMS), starts the cluster, loads the images, creates a random MinIO password
(kept in `state/minio-password`, readable only by you), loads the data into MinIO and deploys the backends and the
app. It is safe to re-run.

On old kernels (below 5.10, e.g. Ubuntu 20.04's 5.4) the runc inside minikube's node cannot start any container
("can't mask dir /proc/acpi ... invalid argument"), so `install.sh` swaps in the bundled `bin/runc-node` while the
cluster boots. Force it with `IAMIQ_RUNC_PATCH=1` or turn it off with `IAMIQ_RUNC_PATCH=0`. If a cluster was
already created without the patch, delete it first (`./iamiq.sh uninstall`), because kubeadm never finished there.

## Use

```bash
./iamiq.sh open                                   # on the server: app on 127.0.0.1:5000
ssh -L 5000:127.0.0.1:5000 USER@SERVER            # on your machine, then open http://localhost:5000/
./iamiq.sh status | stop | start | logs <deployment> | uninstall
```

## Network exposure

Nothing is reachable from outside the server:

- every Kubernetes Service is `ClusterIP` (no NodePort), so the backends, MinIO and the app are only reachable
  inside the cluster;
- minikube publishes its own ports (API server, SSH) on `127.0.0.1` only (`--listen-address=127.0.0.1`);
- the app is reached through `kubectl port-forward --address 127.0.0.1` plus an SSH tunnel;
- MinIO uses a generated password, not the default `minioadmin`.

On a shared server, other users logged in to the same machine can reach `127.0.0.1:5000` while `./iamiq.sh open` is
running. Stop it when you are done.

## Contents

| Path | What |
|---|---|
| `images/` | the app, 7 backend images (`imafusa/backend` runs all 7 ImAFUSA tools) and MinIO, as `docker save` tarballs |
| `manifests/` | the k8s manifests, hardened (ClusterIP, MinIO login from the Secret `iam-datalake-credentials`) |
| `sample_data/` | the real partner data, loaded into MinIO by `load_sample_data.py` (see the repo's `backends/README.md`) |
| `bin/` | `minikube`, `kubectl` and `runc-node` (an older runc, swapped into the node on kernels < 5.10) |
| `state/` | created by `install.sh`: minikube state, kubeconfig, the MinIO password |
| `VERSIONS`, `SHA256SUMS` | what was packaged, from which commit, and checksums |

The pollution tool has no data (its 179 GB zarr store is not included) and shows "data coming soon".

"""Citizen-friendly labels for optional proposal changes."""
ASPECT_LABELS={'personal_privacy':'cameras viewing private spaces','perceived_safety':'physical safety','data_security':'security and access to data',
    'medical_public_benefit':'the medical purpose','distributive_equity':'fair access to benefits','acoustic_impact':'noise',
    'aesthetic_clutter':'visual clutter','visible_physical_intrusion':'visible aircraft','system_reliability':'technical reliability',
    'participation_skills':'residents learning how to participate and report problems',
    'training':'training and learning opportunities','airspace_traffic':'keeping aircraft safely separated in shared airspace',
    'rotor_wind':'air pushed down by the rotors',
    'awareness':'public information about the proposal','institutional_trust':'trust in the institutions responsible',
    'urban_mobility_plan':'integration with the city’s transport plans',
    'facility_siting':'where landing and support facilities would be located','land_allocation':'land allocated to drone facilities',
    'energy_demand':'energy use','emissions':'emissions',
    'cost_financing':'costs and how they would be funded','business_viability':'the service’s financial viability',
    'remote_access':'access for remote communities','vulnerable_access':'access for vulnerable groups',
    'transport_connections':'connections with other transport services','congestion':'effects on traffic congestion'}


def aspect_label(facet):return ASPECT_LABELS.get(facet,facet.replace('_',' '))

import pandas as pd


def load_data():
    return pd.read_excel("../data/get_around_delay_analysis.xlsx")


def prepare_rentals(df):
    rentals_with_previous = df[df['previous_ended_rental_id'].notna()].copy()
    rentals_with_previous['previous_ended_rental_id'] = rentals_with_previous['previous_ended_rental_id'].astype(int)

    rentals = rentals_with_previous.merge(df, how='left', left_on='previous_ended_rental_id', right_on='rental_id', suffixes=('', '_previous'))
    rentals = rentals.drop(columns=[
        'delay_at_checkout_in_minutes',
        'previous_ended_rental_id_previous',
        'time_delta_with_previous_rental_in_minutes_previous',
        'rental_id_previous',
        'car_id_previous',
    ])

    rentals_with_known_delay = rentals[rentals['delay_at_checkout_in_minutes_previous'].notna()]
    return rentals_with_known_delay


def indicateurs(rentals_with_known_delay, threshold):
    rentals_with_threshold = rentals_with_known_delay[rentals_with_known_delay['time_delta_with_previous_rental_in_minutes'] >= threshold]

    en_retard = rentals_with_threshold['delay_at_checkout_in_minutes_previous'] > 0
    probleme = rentals_with_threshold['delay_at_checkout_in_minutes_previous'] > rentals_with_threshold['time_delta_with_previous_rental_in_minutes']

    locations_bloquees = len(rentals_with_known_delay) - len(rentals_with_threshold)

    return {
        "locations bloquées": locations_bloquees,
        "% locations bloquées": locations_bloquees / len(rentals_with_known_delay) * 100,
        "% retards": en_retard.mean() * 100,
        "% problematiques": probleme.mean() * 100,
        "% problematiques sur retards": probleme.sum() / en_retard.sum() * 100,
    }

def statut_locations(rentals_with_known_delay, threshold):
    graph = rentals_with_known_delay.copy()
    graph['bloquee'] = graph['time_delta_with_previous_rental_in_minutes'] < threshold
    graph['problematique'] = graph['delay_at_checkout_in_minutes_previous'] > graph['time_delta_with_previous_rental_in_minutes']

    graph['statut'] = graph['problematique'].map({True: 'Problématique', False: 'Sans problème'}) + ' ' + graph['bloquee'].map({True: 'bloquée', False: 'non bloquée'})
    return graph

def tableau_seuils(rentals_with_known_delay):
    lignes = []

    for threshold in range(0, 721, 30):
        rentals_with_threshold = rentals_with_known_delay[rentals_with_known_delay['time_delta_with_previous_rental_in_minutes'] >= threshold]

        en_retard = rentals_with_threshold['delay_at_checkout_in_minutes_previous'] > 0
        probleme = rentals_with_threshold['delay_at_checkout_in_minutes_previous'] > rentals_with_threshold['time_delta_with_previous_rental_in_minutes']

        lignes.append({
            'threshold': threshold,
            'locations restantes': len(rentals_with_threshold),
            'locations bloquées': len(rentals_with_known_delay) - len(rentals_with_threshold),
            'retards': en_retard.sum(),
            'problématiques': probleme.sum(),
        })

    tableau = pd.DataFrame(lignes)
    tableau['problématiques empêchées'] = tableau['problématiques'].iloc[0] - tableau['problématiques']
    return tableau


def gain_par_tranche(tableau):
    gain = pd.DataFrame({
        'de': tableau['threshold'] - 30,
        'à': tableau['threshold'],
        'locations bloquées en plus': tableau['locations bloquées'].diff(),
        'problèmes évités en plus': tableau['problématiques empêchées'].diff(),
    })
    gain = gain.dropna().astype(int)
    return gain

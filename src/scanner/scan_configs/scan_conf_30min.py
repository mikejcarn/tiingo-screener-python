scan_conf = {

    # 30min ==============================================

    '30min_aVWAPChannelResistance': {
        'criteria': {
            '30min': ['aVWAP_channel'],
        },
        'params': {
            'aVWAP_channel': {
                '30min': [
                    {'mode': 'resistance', 'distance_pct': 3.0, 'direction': 'within'},
                ]
            },
        }
    },

}

#!/usr/bin/python3

"""zabbix rubrik

Copyright 2022 Olivier DRAGHI

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import argparse
import yaml
import urllib3
import json
import rubrik_cdm
from pyzabbix import ZabbixMetric, ZabbixSender
from socket import gethostname

CONFIG_FILE = "/etc/zabbix-rubrik/zabbix-rubrik.yaml"

CONFIG={}
DEBUG=False
METRICS_SYSTEM_STORAGE = ('total', 'used', 'available', 'snapshot', 'liveMount', 'pendingSnapshot', 'cdp', 'miscellaneous', 'lastUpdateTime')
METRIC_RUNWAY_REMAINING = ('runway_remaining',)  # Warning: This is a tuple of one metric. keep the comma.. 
METRICS = METRICS_SYSTEM_STORAGE + METRIC_RUNWAY_REMAINING

def debug(message):
    if DEBUG:
        print("DEBUG: " + message)


def load_config(region):
    global CONFIG
    with open(CONFIG_FILE, "r") as config_file:
        cfg = yaml.safe_load(config_file)

    # ZABBIX Endpoint
    try:
        CONFIG['zabbix_server'] = cfg['zabbix']['server']
    except KeyError:
        CONFIG['zabbix_server'] = '127.0.0.1'
    try:
        CONFIG['zabbix_port'] = cfg['zabbix']['port']
    except KeyError:
        CONFIG['zabbix_port'] = '10051'
    try:
        CONFIG['zabbix_host_name'] = cfg['zabbix']['host_name']
    except KeyError:
        CONFIG['zabbix_host_name'] = gethostname()

    # Rubrik Endpoint
    try:
        cfg_rubrik={[*rbk][0]:[*rbk.values()][0] for rbk in cfg['rubrik']}
        CONFIG['node'] = cfg_rubrik[region]['node']
        CONFIG['api_token'] = cfg_rubrik[region]['api_token']
    except KeyError:
        CONFIG['node'] = None
        CONFIG['api_token'] = None


def parse_arguments():
    """Parse command line arguments 

    Returns:
        tuple: discovery, region , metric
    """
    global DEBUG
    parser = argparse.ArgumentParser(
        description='Zabbix Sender from Rubrik metrics')
    parser.add_argument('-d', '--debug', required=False, action='store_true',
                        help='Debug mode')
    parser.add_argument('--discovery', required=False, action='store_true',
                        help='Return {#RUBRIKSITE} json')
    parser.add_argument('-r', '--region', required=False,
                        help='cbv | vdr    (Mandatory when not in discovery mode)')
    parser.add_argument('-m', '--metric', required=False,
                        help=' | '.join(METRICS) )
    parser.add_argument('--send', required=False, action='store_true',
                        help='Send all metrics to zabbix')
    args = parser.parse_args()

    if args.debug:
        DEBUG=True
        print("*** Debug mode is ON ***")
    
    discovery = args.discovery
    sender_mode = args.send

    if discovery:
        sender_mode = False
    
    debug(f"Sender mode '{sender_mode}'")

    if not discovery and not args.region:
        exit("--region is requiered when we are not in discovery mode.")
    
    if args.metric and str(args.metric) not in METRICS:
        exit(f"Invalid metric in command arg.\nValid metrics are {METRICS}")
    debug(f"Metric '{args.metric}'")
    
    region=str(args.region).lower()
    debug(f"Region '{region}'")
    
    if args.metric and args.send:
        exit("Send to zabbix is only available from whitout --metric argument.")

    return discovery, region, args.metric, sender_mode


def get_rubrik_stat(metric=None):
    """Query Rubrik for metrics

    Args:
        metric (str): optional is null return all metrics in 

    Returns:
        any: Value of the asked metric
        dict: Dict of all metrics when arg 'metric' is null
    """
    rubrik = rubrik_cdm.Connect(node_ip=CONFIG['node'], api_token=CONFIG['api_token'])
    
    if metric in METRICS_SYSTEM_STORAGE:
        system_storage=rubrik.get('internal', '/stats/system_storage')
        debug(f"system_storage: {system_storage}")
        debug(f"{metric}: {system_storage[metric]}")
        return system_storage[metric]
    
    if metric in METRIC_RUNWAY_REMAINING:
        runway_remaining=rubrik.get('internal', '/stats/runway_remaining')
        debug(f"runway_remaining: {runway_remaining}")
        return runway_remaining['days']
    
    # All metrics
    system_storage=rubrik.get('internal', '/stats/system_storage')
    runway_remaining=rubrik.get('internal', '/stats/runway_remaining')
    metrics=system_storage
    metrics['runway_remaining']=runway_remaining['days']
    return metrics

def make_zabbix_packet(region, metrics):
    hostanme = CONFIG['zabbix_host_name']
    packet=[]
    for m in metrics:
        key = zabbix_key(region, m)
        val = metrics[m]
        packet.append( ZabbixMetric(hostanme, key, val) )
        debug(f"Packet.add  hostanme: {hostanme}, key: {key}, val:{val}")
    return packet

def send_zabbix_data(packet):
    server = ZabbixSender( zabbix_server=CONFIG['zabbix_server'], zabbix_port=int( CONFIG['zabbix_port'] ) )
    result = server.send(packet)
    debug( str( server ) )
    debug( str( result ) )


def zabbix_key(region, metric):
    if metric in METRICS_SYSTEM_STORAGE:
        return f"rubrik.stats.system_storage.{metric}[{region}]"
    if metric in METRIC_RUNWAY_REMAINING:
        return f"rubrik.stats.runway_remaining[{region}]"

def config_discovery():
    """ Print rubrik discovery for in json for Zabbix
    Exemple:
        [
            {"{#RUBRIKSITE}":"cbv"},
            {"{#RUBRIKSITE}":"vdr"}
        ]
    """
    with open(CONFIG_FILE, "r") as config_file:
        cfg = yaml.safe_load(config_file)
    try:
        # discovery =  [ { '{#RUBRIKSITE}' : list(region.keys())[0] } for region in cfg['rubrik'] ]
        discovery =  [ { '{#RUBRIKSITE}' : [*region][0] } for region in cfg['rubrik'] ]
        print(json.dumps(discovery))
    except KeyError:
        exit(f"'rubrik' is not found in the configuration file ({CONFIG_FILE})")


def main():
    # Disable certificate warnings and connect to Rubrik Cluster
    urllib3.disable_warnings()

    discovery, region, metric, sender_mode = parse_arguments()

    if discovery:
        config_discovery()
        return

    load_config(region)
    debug(f"Zabbix target is '{CONFIG['zabbix_server']}:{CONFIG['zabbix_port']}'")
    debug(f"Region '{region}'")
    debug(f"Rubrik Endpoint is '{CONFIG['node']}'")

    if metric:
        print(get_rubrik_stat(metric))
        return

    metrics = get_rubrik_stat()

    if not sender_mode:
        print(metrics)
        return
    
    packet = make_zabbix_packet(region, metrics)
    send_zabbix_data(packet)


if __name__ == '__main__':
    main()

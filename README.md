# Zabbix - Rubrik 
![GitHub](https://img.shields.io/github/license/odraghi/zabbix-rubrik?style=flat-square)

Export Rubrik stats to Zabbix

## How it works

1. Discovery - Zabbix query the server to discover rubrik site
2. Trigger   - Zabbix query the server to send rubrik stats for a site


## Prerequisite

Install and configure zabbix-client.

This is not this project purpose but here a sample to do that.

On Ubuntu :
```bash
apt-get install zabbix-agent
```

## Install

Copy the package 'zabbix-rubrik.tar.gz' on zabbix client.

```bash
[ ! -d /appli ] && mkdir /appli
tar --directory=/appli -xzvf zabbix-rubrik.tar.gz

# Install python modules
cd /appli/zabbix-rubrik/ ; python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
deactivate

chown -R zabbix:zabbix /appli/zabbix-rubrik
chmod 640 /appli/zabbix-rubrik/etc/zabbix-rubrik.yaml

# Very important as we look for configuration files in /etc/zabbix-rubrik
ln -s /appli/zabbix-rubrik/etc /etc/zabbix-rubrik

# Try to find zabbix config dir
[ -d /etc/zabbix/zabbix_agentd.d/ ] && ZABBIX_AGENTD_DIR="/etc/zabbix/zabbix_agentd.d/"
[ -d /etc/zabbix/zabbix_agentd.conf.d/ ] && ZABBIX_AGENTD_DIR="/etc/zabbix/zabbix_agentd.conf.d/"

[ -z ${ZABBIX_AGENTD_DIR} ] && echo "WARN: Zabbix agentd config dir not found. You should link manually 'zabbix-rubrik_userparameters.conf'"
[ ! -z ${ZABBIX_AGENTD_DIR} ] && ln -s /appli/zabbix-rubrik/etc/zabbix-rubrik_userparameters.conf ${ZABBIX_AGENTD_DIR}
```

## Update

```bash
tar --directory=/appli -xzvf zabbix-rubrik.tar.gz
chown -R zabbix:zabbix /appli/zabbix-rubrik
chmod 640 /appli/zabbix-rubrik/etc/zabbix-rubrik.yaml
```

## Configuration

To run proprely we need to have a user on the rubrk
1. Create a user on rubrik (privilege: admin readonly)
2. Generate an API token for this user

Sample configuration with 2 sites (#RUBRIKSITE):
- region-eu-central-1
- region-eu-west-1

/appli/zabbix-rubrik/etc/zabbix-rubrik.yaml
```yaml
zabbix:
  server: 'x.x.x.x'
  port: '10051'

rubrik:
  - region-eu-central-1:
      node: 'rubrik-node.eu-central-1.local'
      api_token : 'xxxxxxxxxxxxx'
  - region-eu-west-1:
      node: 'rubrik-node.eu-west-1.local'
      api_token : 'xxxxxxxxxxxxx'
```

WARNING. As we need API Tokens please take care of configuration file permissions to avoid unexcpected user access. 
```bash
chown -R zabbix:zabbix /appli/zabbix-rubrik
chmod 640 /appli/zabbix-rubrik/etc/zabbix-rubrik.yaml
```

## Discovery

```bash
/appli/zabbix-rubrik/bin/zabbix-rubrik-discovery.sh
```

Return a json array of objets with attribut named "{#RUBRIKSITE}"

Sample:

```json
[
    {"{#RUBRIKSITE}":"region-eu-central-1"},
    {"{#RUBRIKSITE}":"region-eu-west-1"}
]
```

## Trigger

```bash
/appli/zabbix-rubrik/bin/zabbix-rubrik-send.sh
```

When triggered, we use zabbix-send to send all metrics in a single packet to zabbix server.

## Debug

You can call scripts with '--debug' or '-d' .

```bash
/appli/zabbix-rubrik/bin/zabbix-rubrik-discovery.sh --debug

/appli/zabbix-rubrik/bin/zabbix-rubrik.sh region-eu-central-1 --debug

/appli/zabbix-rubrik/bin/zabbix-rubrik-send.sh region-eu-central-1 --debug
```

## Advanced mode

You can directly call zabbix-rubrik.py this way.

```bash
## Prerequisite: Activate virtual env
source /appli/zabbix-rubrik/env/bin/activate

# Help
python3 /appli/zabbix-rubrik/src/zabbix-rubrik.py -h

# Discovery
python3 /appli/zabbix-rubrik/src/zabbix-rubrik.py --discovery

# Get all metrics
python3 /appli/zabbix-rubrik/src/zabbix-rubrik.py --region region-eu-central-1 --debug

# Get metric: total
python3 /appli/zabbix-rubrik/src/zabbix-rubrik.py --region region-eu-central-1 --metric total --debug

# Get metric: available
python3 /appli/zabbix-rubrik/src/zabbix-rubrik.py --region region-eu-central-1 --metric available --debug

## End: Deactivate virtual env OR exit
deactivate
```

## Metrics

|Key                                                        |  type | unit  | Description                                         |
|----------------------------------------------------------:|------:|------:|----------------------------------------------------:|
|rubrik.stats.system_storage.total[#RUBRIKSITE]             |  int  | bytes | System storage Total                                |
|rubrik.stats.system_storage.used[#RUBRIKSITE]              |  int  | bytes | System storage Used                                 |
|rubrik.stats.system_storage.available[#RUBRIKSITE]         |  int  | bytes | System storage Available                            |
|rubrik.stats.system_storage.snapshot[#RUBRIKSITE]          |  int  | bytes | System storage Snapshot                             |
|rubrik.stats.system_storage.liveMount[#RUBRIKSITE]         |  int  | bytes | System storage Live Mount                           |
|rubrik.stats.system_storage.pendingSnapshot[#RUBRIKSITE]   |  int  | bytes | System storage Pening Snapshot                      |
|rubrik.stats.system_storage.cdp[#RUBRIKSITE]               |  int  | bytes | System storage Continuous Data Protection           |
|rubrik.stats.system_storage.miscellaneous[#RUBRIKSITE]     |  int  | bytes | System storage Miscellaneous                        |
|rubrik.stats.system_storage.lastUpdateTime[#RUBRIKSITE]    |  date | date  | System storage last Update Time                     |
|rubrik.stats.runway_remaining[#RUBRIKSITE]                 |  int  | days  | Number of days remaining before the system fills up |


## Template Zabbix

Sample:
-  src/zabbix-rubrik-templates.xml

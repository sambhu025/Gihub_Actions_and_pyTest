import json
import time
from collections import namedtuple
from jsonpath_ng.ext import parse
from ixnetwork_restpy import SessionAssistant, StatViewAssistant
from abstract_open_traffic_generator.api import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.control import *
from ixnetwork_open_traffic_generator.validation import Validation
from ixnetwork_open_traffic_generator.vport import Vport
from ixnetwork_open_traffic_generator.ngpf import Ngpf
from ixnetwork_open_traffic_generator.trafficitem import TrafficItem


class IxNetworkApi(Api):
    """IxNetwork implementation of the abstract-open-traffic-generator package

    Args
    ----
    - address (str): The address of the IxNetwork API Server
    - port (str): The rest port of the IxNetwork API Server
    - username (str): The username for Linux IxNetwork API Server multi session environments
        This is not required when connecting to single session environments
    - password (str): The password for Linux IxNetwork API Server multi session environments
        This is not required when connecting to single session environments
    """
    def __init__(self,
                 address='127.0.0.1',
                 port='11009',
                 username='admin',
                 password='admin',
                 license_servers=[]):
        """Create a session
        - address (str): The ip address of the TestPlatform to connect to 
        where test sessions will be created or connected to.
        - port (str): The rest port of the TestPlatform to connect to.
        - username (str): The username to be used for authentication
        - password (str): The password to be used for authentication
        """
        super(IxNetworkApi, self).__init__()
        self._address = address
        self._port = port
        self._username = username
        self._password = password
        self._license_servers = license_servers
        self._running_config = None
        self._config = None
        self._assistant = None
        self.validation = Validation(self)
        self.vport = Vport(self)
        self.ngpf = Ngpf(self)
        self.traffic_item = TrafficItem(self)

    @property
    def config(self):
        return self._config

    def get_config_object(self, name):
        return self._config_objects[name]

    @property
    def ixn_objects(self):
        """A dict of all model unique names to ixn hrefs
        """
        return self._ixn_objects

    def get_ixn_object(self, name):
        """Returns an ixnetwork_restpy object given a unique configuration name
        """
        href = self.get_ixn_href(name)
        return self._assistant.Session.GetObjectFromHref(href)

    def get_ixn_href(self, name):
        """Returns an href given a unique configuration name
        """
        return self._ixn_objects[name]

    @property
    def assistant(self):
        return self._assistant

    def _dict_to_obj(self, source):
        """Returns an object given a dict
        """
        if isinstance(source, list):
            source = [self._dict_to_obj(x) for x in source]
        if not isinstance(source, dict):
            return source
        o = lambda: None
        for k, v in source.items():
            o.__dict__[k] = self._dict_to_obj(v)
        return o

    def set_state(self, state):
        """Abstract API implementation
        """
        if isinstance(state, (State, str, dict, type(None))) is False:
            raise TypeError(
                'The content must be of type (Config, str, dict, type(None))' %
                Config.__class__)
        if isinstance(state, str) is True:
            state = self._dict_to_obj(json.loads(state))
        elif isinstance(state, dict) is True:
            state = self._dict_to_obj(state)
        if state.choice == 'config_state':
            self._set_config_state(state.config_state)
        elif state.choice == 'flow_transmit_state':
            self._set_flow_transmit_state(state.flow_transmit_state)
        elif state.choice == 'port_capture_state':
            self._set_port_capture_state(state.port_capture_state)

    def _set_config_state(self, config_state):
        """Set or update the configuration
        """
        self._config = config_state.config
        self._config_objects = {}
        self._ixn_objects = {}
        self._capture_request = None
        self._errors = []
        self.validation.validate_config()
        self._connect()
        if self._config is None:
            self._ixnetwork.NewConfig()
        else:
            start = time.time()
            self.vport.config()
            self.info('ports configuration %ssecs' %
                                 str(time.time() - start))
            start = time.time()
            self.ngpf.config()
            self.info('devices configuration %ssecs' %
                                 str(time.time() - start))
            start = time.time()
            self.traffic_item.config()
            self.info('flows configuration %ssecs' %
                                 str(time.time() - start))
        self._running_config = self._config

    def _set_flow_transmit_state(self, flow_transmit_state):
        """Set the transmit state of flows
        """
        return self.traffic_item.transmit(flow_transmit_state)

    def _set_port_capture_state(self, request):
        """Starts capture on all ports that have capture enabled.
        """
        self._capture_request = request

    def _start_capture(self):
        if self._capture_request is not None:
            payload = {'arg1': []}
            for vport in self.select_vports().values():
                payload['arg1'].append(vport['href'])
            url = '%s/vport/operations/clearCaptureInfos' % self._ixnetwork.href
            response = self._request('POST', url, payload)
            self._ixnetwork.StartCapture()

    def get_capture_results(self, request):
        """Gets capture file and returns it as a byte stream
        """
        capture = self._vport.find(Name=request.port_name).Capture
        capture.Stop('allTraffic')
        time.sleep(3)

        payload = {'arg1': [self._vport.href]}
        url = '%s/vport/operations/getCaptureInfos' % self._ixnetwork.href
        response = self._request('POST', url, payload)
        file_name = response['result'][0]['arg6']
        file_id = response['result'][0]['arg1']

        url = '%s/vport/operations/saveCaptureInfo' % self._ixnetwork.href
        payload = {'arg1': self._vport.href, 'arg2': file_id}
        response = self._request('POST', url, payload)

        path = '%s/capture' % self._ixnetwork.Globals.PersistencePath
        url = '%s/files?absolute=%s&filename=%s.cap' % (self._ixnetwork.href,
                                                        path, file_name)
        pcap_file_bytes = self._request('GET', url)
        return pcap_file_bytes

    def get_port_results(self, request):
        """Abstract API implementation
        """
        return self.vport.results(request)

    def get_flow_results(self, request):
        """Abstract API implementation

        Args
        ----
        - request (Union[FlowRequest, str, dict]): A request for flow results.
            The request content MUST be based on the OpenAPI #/components/schemas/Result.FlowRequest model.
            See the docs/openapi.yaml document for all model details.
        """
        from abstract_open_traffic_generator.result import FlowRequest
        self._errors = []
        if isinstance(request, (FlowRequest, str, dict)) is False:
            raise TypeError(
                'The content must be of type Union[FlowRequest, str, dict]')
        if isinstance(request, str) is True:
            request = json.loads(
                request,
                object_hook=lambda otg: namedtuple('otg', otg.keys())
                (*otg.values()))
        elif isinstance(request, dict) is True:
            request = namedtuple('otg', request.keys())(*request.values())
        response = self.traffic_item.results(request)
        if len(self._errors) > 0:
            raise Exception('\n'.join(self._errors))
        return response

    def add_error(self, error):
        """Add an error to the global errors
        """
        if isinstance(error, str) is False:
            self._errors.append(str(error))
        else:
            self._errors.append(error)

    def _connect(self):
        """Connect to an IxNetwork API Server.
        """
        if self._assistant is None:
            self._assistant = SessionAssistant(
                IpAddress=self._address,
                RestPort=self._port,
                UserName=self._username,
                Password=self._password,
                LogLevel=SessionAssistant.LOGLEVEL_INFO)
            self._ixnetwork = self._assistant.Session.Ixnetwork
            self._vport = self._ixnetwork.Vport
            self._topology = self._ixnetwork.Topology
            self._traffic = self._ixnetwork.Traffic
            self._traffic_item = self._ixnetwork.Traffic.TrafficItem
            if len(self._license_servers) > 0:
                self._ixnetwork.Globals.Licensing.LicensingServers = self._license_servers

    def _request(self, method, url, payload=None):
        connection, url = self._assistant.Session._connection._normalize_url(
            url)
        headers = {}
        if payload is not None:
            payload = json.dumps(payload)
            headers['Content-Type'] = 'application/json'
        response = self._assistant.Session._connection._session.request(
            method, url, headers=headers, data=payload, verify=False)
        response.raise_for_status()
        if response.status_code == 202:
            content = response.json()
            while content['state'] == 'IN_PROGRESS':
                time.sleep(1)
                response = self._request('GET', content['url'])
        if response.headers.get('Content-Type'):
            if response.headers['Content-Type'] == 'application/json':
                return response.json()
            elif response.headers[
                    'Content-Type'] == 'application/octet-stream':
                return response.content
        return response

    def _remove(self, ixn_obj, items):
        """Remove any ixnetwork objects that are not found in the items list.
        If the items list does not exist remove everything.
        """
        valid_names = [item.name for item in items]
        invalid_names = []
        for item in ixn_obj.find():
            if item.Name not in valid_names:
                invalid_names.append(item.Name)
        if len(invalid_names) > 0:
            ixn_obj.find(Name='^(%s)$' % '|'.join(invalid_names)).remove()

    def _get_topology_name(self, port_name):
        return 'Topology %s' % port_name

    def select_chassis_card(self, vport):
        pieces = vport['connectionStatus'].split(';')
        payload = {
            'selects': [{
                'from':
                '/availableHardware',
                'properties': [],
                'children': [{
                    'child':
                    'chassis',
                    'properties': [],
                    'filters': [{
                        'property': 'hostname',
                        'regex': '^%s$' % pieces[0]
                    }]
                }, {
                    'child':
                    'card',
                    'properties': ['*'],
                    'filters': [{
                        'property': 'cardId',
                        'regex': '^%s$' % int(pieces[1])
                    }]
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]['chassis'][0]['card'][0]

    def select_vports(self):
        """Select all vports.
        Return them in a dict keyed by vport name.
        """
        payload = {
            'selects': [{
                'from':
                '/',
                'properties': [],
                'children': [{
                    'child':
                    'vport',
                    'properties': [
                        'name', 'type', 'location', 'connectionState',
                        'connectionStatus', 'assignedTo', 'connectedTo'
                    ],
                    'filters': []
                }, {
                    'child': 'l1Config',
                    'properties': ['currentType'],
                    'filters': []
                }, {
                    'child': '^(eth.*|novus.*|uhd.*|atlas.*|ares.*|star.*)$',
                    'properties': ['*'],
                    'filters': []
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        vports = {}
        if 'vport' in results[0]:
            for vport in results[0]['vport']:
                vports[vport['name']] = vport
        return vports

    def select_traffic_items(self, traffic_item_filters=[]):
        """Select all traffic items.
        Return them in a dict keyed by traffic item name.

        Args
        ----
        - filters (list(dict(property:'', 'regex':''))): A list of filters for the select.
            A filter is a dict with a property name and a regex match
        """
        payload = {
            'selects': [{
                'from':
                '/traffic',
                'properties': [],
                'children': [{
                    'child': 'trafficItem',
                    'properties': ['name', 'state', 'enabled'],
                    'filters': traffic_item_filters
                }, {
                    'child': 'highLevelStream',
                    'properties': ['txPortName', 'rxPortNames'],
                    'filters': []
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        traffic_items = {}
        try:
            for traffic_item in results[0]['trafficItem']:
                traffic_items[traffic_item['name']] = traffic_item
        except:
            pass
        return traffic_items

    def select_chassis_card_port(self, location):
        """Select all availalehardware.
        Return them in a dict keyed by vport name.
        """
        (hostname, cardid, portid) = location.split(';')
        payload = {
            'selects': [{
                'from':
                '/availableHardware',
                'properties': [],
                'children': [{
                    'child':
                    'chassis',
                    'properties': [],
                    'filters': [{
                        'property': 'hostname',
                        'regex': '^%s$' % hostname
                    }]
                }, {
                    'child':
                    'card',
                    'properties': [],
                    'filters': [{
                        'property': 'cardId',
                        'regex': '^%s$' % abs(int(cardid))
                    }]
                }, {
                    'child':
                    'port',
                    'properties': [],
                    'filters': [{
                        'property': 'portId',
                        'regex': '^%s$' % abs(int(portid))
                    }]
                }],
                'inlines': []
            }]
        }
        url = '%s/operations/select?xpath=true' % self._ixnetwork.href
        results = self._ixnetwork._connection._execute(url, payload)
        return results[0]['chassis'][0]['card'][0]['port'][0]['xpath']

    def clear_ownership(self, hrefs):
        if len(hrefs) > 0:
            self.info('Pre-empting locations [%s]' %
                                 ', '.join([href for href in hrefs.keys()]))
            url = '%s/operations/clearownership' % [
                href for href in hrefs.values()
            ][0]
            payload = {'arg1': [href for href in hrefs.values()]}
            results = self._ixnetwork._connection._execute(url, payload)
            time.sleep(2)

    def get_config(self):
        return self._config

    def check_protocol_statistics(self):
        view = StatViewAssistant(self._ixnetwork, 'Protocols Summary')
        view.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, 0)
        view.CheckCondition('Sessions Down', StatViewAssistant.EQUAL, 0)

    def info(self, message):
        self._ixnetwork.info('[ixn-otg] %s' % message)

    def warning(self, message):
        self._ixnetwork.warn('[ixn-otg] %s' % message)

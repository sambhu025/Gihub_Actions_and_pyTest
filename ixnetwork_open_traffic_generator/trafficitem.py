import json
import time
from ixnetwork_open_traffic_generator.customfield import CustomField
from ixnetwork_restpy import StatViewAssistant


class TrafficItem(CustomField):
    """TrafficItem configuration

    Args
    ----
    - ixnetworkapi (IxNetworkApi): instance of the ixnetworkapi class
    
    """
    _RESULT_COLUMNS = [
        'name',
        'state',
        'port_tx',
        'port_rx',
        'frames_tx',
        'frames_rx',
        'frames_tx_rate',
        'frames_rx_rate',
        'bytes_tx_rate',
        'bytes_rx_rate',
        'loss',
    ]
    
    _STACK_IGNORE = [
        'ethernet.fcs'
    ]

    _TYPE_TO_HEADER = {
        'ethernet': 'ethernet',
        'pfcPause': 'pfc_pause',
        'vlan': 'vlan',
        'ipv4': 'ipv4',
        "tcp" : "tcp",
        "udp" : "udp",
        'custom': 'custom'
    }

    _HEADER_TO_TYPE = {
        'ethernet': 'ethernet',
        'pfcpause': 'pfcPause',
        'vlan': 'vlan',
        'ipv4': 'ipv4',
        "tcp" : "tcp",
        "udp" : "udp",
        'custom': 'custom'
    }

    _BIT_RATE_UNITS_TYPE = {
        'bps' : 'bitsPerSec',
        'kbps' : 'kbitsPerSec',
        'mbps' : 'mbitsPerSec',
        'gbps' : 'mbytesPerSec'
    }
    
    _PFCPAUSE = {
        'dst': 'pfcPause.header.header.dstAddress',
        'src': 'pfcPause.header.header.srcAddress',
        'ether_type': 'pfcPause.header.header.ethertype',
        'control_op_code': 'pfcPause.header.macControl.controlOpcode',
        'class_enable_vector': 'pfcPause.header.macControl.priorityEnableVector',
        'pause_class_0': 'pfcPause.header.macControl.pauseQuanta.pfcQueue0',
        'pause_class_1': 'pfcPause.header.macControl.pauseQuanta.pfcQueue1',
        'pause_class_2': 'pfcPause.header.macControl.pauseQuanta.pfcQueue2',
        'pause_class_3': 'pfcPause.header.macControl.pauseQuanta.pfcQueue3',
        'pause_class_4': 'pfcPause.header.macControl.pauseQuanta.pfcQueue4',
        'pause_class_5': 'pfcPause.header.macControl.pauseQuanta.pfcQueue5',
        'pause_class_6': 'pfcPause.header.macControl.pauseQuanta.pfcQueue6',
        'pause_class_7': 'pfcPause.header.macControl.pauseQuanta.pfcQueue7',
    }

    _ETHERNET = {
        'dst': 'ethernet.header.destinationAddress',
        'src': 'ethernet.header.sourceAddress',
        'ether_type': 'ethernet.header.etherType',
        'pfc_queue': 'ethernet.header.pfcQueue',
    }

    _VLAN = {
        'id': 'vlan.header.vlanTag.vlanID',
        'cfi': 'vlan.header.vlanTag.cfi',
        'priority': 'vlan.header.vlanTag.vlanUserPriority',
        'protocol': 'vlan.header.protocolID'
    }

    _IPV4 = {
        'version' : 'ipv4.header.version',
        'header_length' : 'ipv4.header.headerLength',
        'priority' : '_ipv4_priority',
        'total_length': 'ipv4.header.totalLength',
        'identification' : 'ipv4.header.identification',
        'reserved' : 'ipv4.header.flags.reserved',
        'dont_fragment' : 'ipv4.header.flags.fragment',
        'more_fragments' : 'ipv4.header.flags.lastFragment',
        'fragment_offset' : 'ipv4.header.fragmentOffset',
        'time_to_live' : 'ipv4.header.ttl',
        'protocol' : 'ipv4.header.protocol',
        'header_checksum' : 'ipv4.header.checksum',
        'src': 'ipv4.header.srcIp',
        'dst': 'ipv4.header.dstIp',
    }

    _TOS = {
        "precedence": "ipv4.header.priority.tos.precedence",
        "delay": "ipv4.header.priority.tos.delay",
        "throughput": "ipv4.header.priority.tos.throughput",
        "reliability": "ipv4.header.priority.tos.reliability",
        "monetary": "ipv4.header.priority.tos.monetary",
        "unused": "ipv4.header.priority.tos.unused"
    }
    
    _TCP = {
        "src_port" : "tcp.header.srcPort",
        "dst_port" : "tcp.header.dstPort",
        "ecn_ns" : "tcp.header.ecn.nsBit",
        "ecn_cwr" : "tcp.header.ecn.cwrBit",
        "ecn_echo" : "tcp.header.ecn.ecnEchoBit",
        "ctl_urg" : "tcp.header.controlBits.urgBit",
        "ctl_ack" : "tcp.header.controlBits.ackBit",
        "ctl_psh" : "tcp.header.controlBits.pshBit",
        "ctl_rst" : "tcp.header.controlBits.rstBit",
        "ctl_syn" : "tcp.header.controlBits.synBit",
        "ctl_fin" : "tcp.header.controlBits.finBit",
    }
    
    _UDP = {
        "src_port" : "udp.header.srcPort",
        "dst_port" : "udp.header.dstPort",
        "length" : "udp.header.length",
        "checksum" : "udp.header.checksum",
    }
    
    _CUSTOM = '_custom_headers'
    
    def __init__(self, ixnetworkapi):
        self._api = ixnetworkapi
        
    def config(self):
        """Configure config.flows onto Ixnetwork.Traffic.TrafficItem
        
        CRUD
        ----
        - DELETE any TrafficItem.Name that does not exist in config.flows
        - CREATE TrafficItem for any config.flows[*].name that does not exist
        - UPDATE TrafficItem for any config.flows[*].name that exists
        """
        ixn_traffic_item = self._api._traffic_item
        self._api._remove(ixn_traffic_item, self._api.config.flows)
        if self._api.config.flows is not None:
            for flow in self._api.config.flows:
                args = {
                    'Name': flow.name,
                    'TrafficItemType': 'l2L3',
                    'TrafficType': self._get_traffic_type(flow)
                }
                ixn_traffic_item.find(Name='^%s$' % flow.name, TrafficType=args['TrafficType'])
                if len(ixn_traffic_item) == 0:
                    ixn_traffic_item.add(**args)
                else:
                    self._update(ixn_traffic_item, **args)
                self._configure_endpoint(ixn_traffic_item.EndpointSet, flow.tx_rx)
                self._configure_tracking(ixn_traffic_item.Tracking)
                ixn_stream = ixn_traffic_item.ConfigElement.find()
                self._configure_stack(ixn_stream, flow.packet)
                self._configure_size(ixn_stream, flow.size)
                self._configure_rate(ixn_stream, flow.rate)
                self._configure_tx_control(ixn_stream, flow.duration)
                self._configure_options(flow)
    
    def _configure_tracking(self, ixn_tracking):
        ixn_tracking.find()
        if 'trackingenabled0' not in ixn_tracking.TrackBy:
            ixn_tracking.TrackBy = ['trackingenabled0']

    def _configure_options(self, flow):
        enable_min_frame_size = False
        if (len(flow.packet) == 1 and 
            flow.packet[0].choice == 'pfcpause' and 
            flow.size.choice == 'fixed' and 
            flow.size.fixed <= 64):
            enable_min_frame_size = True
        if self._api._traffic.EnableMinFrameSize != enable_min_frame_size:
            self._api._traffic.EnableMinFrameSize = enable_min_frame_size

    def _get_traffic_type(self, flow):
        if flow.tx_rx is None:
            raise ValueError('%s Flow.tx_rx property cannot be None' % flow.name)
        elif flow.tx_rx.choice == 'port':
            encap = 'raw'
        else:
            encap = None
            for name in flow.tx_rx.device.tx_device_names:
                device = self._api.get_config_object(name)
                if device.choice == 'ethernet':
                    encap = 'ethernetVlan'
                elif device.choice == 'bgpv4':
                    encap = 'ipv4'
                else:
                    encap = device.choice
        return encap

    def _configure_endpoint(self, ixn_endpoint_set, endpoint):
        """Transform flow.tx_rx to /trafficItem/endpointSet
        The model allows for only one endpointSet per traffic item
        """
        args = {
            'Sources': [],
            'Destinations' : []
        }
        if (endpoint.choice == "port"):
            args['Sources'].append(self._api.get_ixn_object(endpoint.port.tx_port_name).Protocols.find().href)
            if endpoint.port.rx_port_name != None:
                args['Destinations'].append(self._api.get_ixn_object(endpoint.port.rx_port_name).Protocols.find().href)
        else:
            for port_name in endpoint.device.tx_device_names:
                args['Sources'].append(self._api.get_ixn_href(port_name))
            for port_name in endpoint.device.rx_device_names:
                args['Destinations'].append(self._api.get_ixn_href(port_name))
        ixn_endpoint_set.find()
        if len(ixn_endpoint_set) > 1:
            ixn_endpoint_set.remove()
        if len(ixn_endpoint_set) == 0:
            ixn_endpoint_set.add(**args)
        elif ixn_endpoint_set.Sources != args['Sources'] or ixn_endpoint_set.Destinations != args['Destinations']:
            self._update(ixn_endpoint_set, **args)

    def _update(self, ixn_object, **kwargs):
        from ixnetwork_restpy.base import Base
        update = False
        for name, value in kwargs.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], Base):
                value = [item.href for item in value]
            elif isinstance(value, Base):
                value = value.href
            if getattr(ixn_object, name) != value:
                update = True
        if update is True:
            ixn_object.update(**kwargs)

    def _configure_stack(self, ixn_stream, headers):
        """Transform flow.packets[0..n] to /traffic/trafficItem/configElement/stack
        The len of the headers list is the definitive list which means add/remove
        any stack items so that the stack list matches the headers list.
        If the headers list is empty then use the traffic generator default stack.
        """
        stacks_to_remove = []
        ixn_stack = ixn_stream.Stack.find()
        headers = self.adjust_header(headers)
        for i in range(0, len(headers)):
            header = headers[i]
            if len(ixn_stack) <= i:
                stack = self._add_stack(ixn_stream, stack, header)
            else:
                stack_type_id = ixn_stack[i].StackTypeId
                if stack_type_id in self._STACK_IGNORE:
                    stack = self._add_stack(ixn_stream, stack, header)
                elif stack_type_id not in TrafficItem._TYPE_TO_HEADER:
                    stacks_to_remove.append(ixn_stack[i])
                    stack = self._add_stack(ixn_stream, ixn_stack[i], header)
                elif TrafficItem._TYPE_TO_HEADER[stack_type_id] != header.choice:
                    stacks_to_remove.append(ixn_stack[i])
                    stack = self._add_stack(ixn_stream, ixn_stack[i], header)
                else:
                    stack = ixn_stack[i]
            self._configure_field(stack.Field, header)
        for stack in stacks_to_remove:
            stack.Remove()
    
    def _add_stack(self, ixn_stream, ixn_stack, header):
        type_id = '^%s$' % TrafficItem._HEADER_TO_TYPE[header.choice]
        template = self._api._traffic.ProtocolTemplate.find(StackTypeId=type_id)
        stack_href = ixn_stack.AppendProtocol(template)
        return ixn_stream.Stack.read(stack_href)

    def _configure_field(self, ixn_field, header, field_choice=False):
        """Transform flow.packets[0..n].header.choice to /traffic/trafficItem/configElement/stack/field
        """
        field_map = getattr(self, '_%s' % header.choice.upper())
        packet = getattr(header, header.choice)
        if isinstance(field_map, dict) is False:
            method = getattr(self, field_map)
            method(ixn_field, packet)
            return
        
        for packet_field_name in dir(packet):
            if packet_field_name in field_map:
                pattern = getattr(packet, packet_field_name)
                field_type_id = field_map[packet_field_name]
                self._configure_pattern(ixn_field, field_type_id, pattern, field_choice)

    def _configure_pattern(self, ixn_field, field_type_id, pattern, field_choice=False):
        if pattern == None:
            return
        
        custom_field = getattr(self, field_type_id, None)
        if custom_field is not None:
            custom_field(ixn_field, pattern)
            return

        ixn_field = ixn_field.find(FieldTypeId=field_type_id)
        if pattern.choice == 'fixed':
            ixn_field.update(Auto=False,
                ActiveFieldChoice=field_choice,
                ValueType='singleValue',
                SingleValue=pattern.fixed)
        elif pattern.choice == 'list':
            ixn_field.update(Auto=False,
                ActiveFieldChoice=field_choice,
                ValueType='valueList',
                ValueList=pattern.list)
        elif pattern.choice == 'counter':
            value_type = 'increment' if pattern.counter.up is True else 'decrement'
            ixn_field.update(Auto=False,
                ValueType=value_type,
                ActiveFieldChoice=field_choice,
                StartValue=pattern.counter.start,
                StepValue=pattern.counter.step,
                CountValue=pattern.counter.count)
        elif pattern.choice == 'random':
            ixn_field.update(Auto=False,
                ActiveFieldChoice=field_choice,
                ValueType='repeatableRandomRange',
                MinValue=pattern.random.min,
                MaxValue=pattern.random.max,
                StepValue=pattern.random.step,
                Seed=pattern.random.seed,
                CountValue=pattern.random.count)
        else:
            # TBD: add to set_config errors - invalid pattern specified
            pass
            
        if pattern.ingress_result_name is not None:
            ixn_field.TrackingEnabled = True
            self._api.ixn_objects[pattern.ingress_result_name] = ixn_field.href
    
    def _configure_size(self, ixn_stream, size):
        """ Transform frameSize flows.size to /traffic/trafficItem[*]/configElement[*]/frameSize
        """
        if size is None:
            return
        ixn_frame_size = ixn_stream.FrameSize
        args = {}
        if size.choice == 'fixed':
            args['Type'] = "fixed"
            args['FixedSize'] = size.fixed
        elif size.choice == 'increment':
            args['Type'] = "incrment"
            args['IncrementFrom'] = size.increment.start
            args['IncrementTo'] = size.increment.end
            args['IncrementStep'] = size.increment.step
        elif size.choice == 'random':
            args['Type'] = "random"
            args['RandomMin'] = size.random.min
            args['RandomMax'] = size.random.max
        else:
            print('Warning - We need to implement this %s choice' %size.choice)
        self._update(ixn_frame_size, **args)
            
    def _configure_rate(self, ixn_stream, rate):
        """ Transform frameRate flows.rate to /traffic/trafficItem[*]/configElement[*]/frameRate
        """
        if rate is None:
            return
        ixn_frame_rate = ixn_stream.FrameRate
        args = {}
        if rate.unit == 'line':
            args['Type'] = 'percentLineRate'
        elif rate.unit == 'pps':
            args['Type'] = 'framesPerSecond'
        else:
            args['Type'] = 'bitsPerSecond'
            args['BitRateUnitsType'] = TrafficItem._BIT_RATE_UNITS_TYPE[rate.unit]
        args['Rate'] = rate.value
        self._update(ixn_frame_rate, **args)

    def _configure_tx_control(self, ixn_stream, duration):
        """Transform duration flows.duration to /traffic/trafficItem[*]/configElement[*]/TransmissionControl
        """
        if duration is None:
            return
        ixn_tx_control = ixn_stream.TransmissionControl
        args = {}
        if duration.choice == 'continuous':
            args['Type'] = 'continuous'
            args['MinGapBytes'] = duration.continuous.gap
            args['StartDelay'] = duration.continuous.delay
            args['StartDelayUnits'] = duration.continuous.delay_unit
        elif duration.choice == 'packets':
            args['Type'] = 'fixedFrameCount'
            args['FrameCount'] = duration.packets.packets
            args['MinGapBytes'] = duration.packets.gap
            args['StartDelay'] = duration.packets.delay
            args['StartDelayUnits'] = duration.packets.delay_unit
        elif duration.choice == 'seconds':
            args['Type'] = 'fixedDuration'
            args['Duration'] = duration.seconds.seconds
            args['MinGapBytes'] = duration.seconds.gap
            args['StartDelay'] = duration.seconds.delay
            args['StartDelayUnits'] = duration.seconds.delay_unit
        elif duration.choice == 'burst':
            args['Type'] = 'custom'
            args['BurstPacketCount'] = duration.burst.packets
            args['MinGapBytes'] = duration.burst.gap
            args['EnableInterBurstGap'] = True if duration.burst.gap > 0 else False
            args['InterBurstGap'] = duration.burst.inter_burst_gap
            args['InterBurstGapUnits'] = duration.burst.inter_burst_gap_unit
        self._update(ixn_tx_control, **args)

    def transmit(self, request):
        """Set flow transmit
        1) If start then start any device protocols that are traffic dependent
        2) If start then generate and apply traffic
        3) Execute requested transmit action (start|stop|pause|resume)
        """
        regex = ''
        if request.flow_names is not None and len(request.flow_names) > 0:
            regex = '^(%s)$' % '|'.join(request.flow_names)
        if request.state == 'start':
            self._api._traffic_item.find(Name=regex, State='unapplied')
            if len(self._api._topology.find()) > 0:
                start = time.time()
                self._api._ixnetwork.StartAllProtocols('sync')
                self._api.info('protocols start %ssecs' % str(time.time() - start))
                self._api.check_protocol_statistics()
            if len(self._api._traffic_item) > 0:
                start = time.time()
                self._api._traffic_item.Generate()
                self._api._traffic.Apply()
                self._api.info('flow generate apply %ssecs' % str(time.time() - start))
            self._api._start_capture()
            if len(self._api._traffic_item) > 0:
                start = time.time()
                self._api._ixnetwork.ClearStats(
                    ['waitForPortStatsRefresh', 'waitForTrafficStatsRefresh'])
                self._api.info('flow clear statistics %ssecs' % str(time.time() - start))
        self._api._traffic_item.find(Name=regex)
        if request.state == 'start':
            start = time.time()
            self._api._traffic_item.StartStatelessTrafficBlocking()
            self._api.info('flow start %ssecs' % str(time.time() - start))
        elif request.state == 'stop':
            self._api._traffic_item.StopStatelessTrafficBlocking()
        elif request.state == 'pause':
            self._api._traffic_item.PauseStatelessTrafficBlocking(True)
        elif request.state == 'resume':
            self._api._traffic_item.PauseStatelessTrafficBlocking(False)

    def _set_result_value(self, row, column_name, column_value, column_type = str):
        if len(self._column_names) > 0 and column_name not in self._column_names:
            return
        try:
            row[column_name] = column_type(column_value)
        except:
            if column_type.__name__ in ['float', 'int']:
                row[column_name] = 0
            else:
                row[column_type] = column_value

    def _get_state(self, state):
        """IxNetwork traffic item states
            error, locked, started, 
            startedWaitingForStats, startedWaitingForStreams, stopped, 
            stoppedWaitingForStats, txStopWatchExpected, unapplied
        """
        started_states =  [
            'txStopWatchExpected', 
            'locked', 
            'started', 
            'startedWaitingForStats', 
            'startedWaitingForStreams', 
            'stoppedWaitingForStats'
        ]
        if state in started_states:
            return 'started'
        else:
            return 'stopped'
            
    def results(self, request):
        """Return flow results
        """
        if request.column_names is None:
            self._column_names = []
        else:
            self._column_names = request.column_names
        filter = {
            'property': 'name',
            'regex': '.*'
        }
        if request is not None and request.flow_names is not None and len(request.flow_names) > 0:
            filter['regex'] = '^(%s)$' % '|'.join(request.flow_names)
        flow_rows = {}
        for traffic_item in self._api.select_traffic_items(traffic_item_filters=[filter]).values():
            flow_row = {}
            self._set_result_value(flow_row, 'name', traffic_item['name'])
            self._set_result_value(flow_row, 'transmit', self._get_state(traffic_item['state']))
            self._set_result_value(flow_row, 'port_tx', traffic_item['highLevelStream'][0]['txPortName'])
            self._set_result_value(flow_row, 'port_rx', ' '.join(traffic_item['highLevelStream'][0]['rxPortNames']))
            flow_rows[traffic_item['name']] = flow_row
        try:
            table = self._api.assistant.StatViewAssistant('Traffic Item Statistics')
            table.AddRowFilter('Traffic Item', StatViewAssistant.REGEX, filter['regex'])
            for row in table.Rows:
                flow_row = flow_rows[row['Traffic Item']]
                self._set_result_value(flow_row, 'frames_tx', row['Tx Frames'], int)
                self._set_result_value(flow_row, 'frames_rx', row['Rx Frames'], int)
                self._set_result_value(flow_row, 'bytes_rx', row['Rx Bytes'], int)
                self._set_result_value(flow_row, 'frames_tx_rate', row['Tx Frame Rate'], float)
                self._set_result_value(flow_row, 'frames_rx_rate', row['Rx Frame Rate'], float)
                self._set_result_value(flow_row, 'bytes_tx_rate', row['Tx Rate (Bps)'], float)
                self._set_result_value(flow_row, 'bytes_rx_rate', row['Rx Rate (Bps)'], float)
                self._set_result_value(flow_row, 'loss', row['Loss %'], float)
        except Exception as e:
            self._api.add_error(e)
        return flow_rows.values()

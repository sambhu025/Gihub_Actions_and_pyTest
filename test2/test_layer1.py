import pytest
from abstract_open_traffic_generator.port import *
from abstract_open_traffic_generator.config import *
from abstract_open_traffic_generator.layer1 import *
from abstract_open_traffic_generator.control import *


def test_layer1(serializer, api):
    """Test that layer1 configuration settings are being applied correctly
    A user should be able to configure ports with/without locations.
    The expectation should be if a location is configured the user wants to 
    connect but debug should allow for config creation without location.
    Ports with no location should not generate an error message.
    Ports with location should generate an error message if unable to connect.
    """
    port1 = Port(name='port1', location='10.39.35.12;09;01')
    port2 = Port(name='port2', location='10.39.35.12;09;02')
    port3 = Port(name='port no location')
    ethernet = Layer1(name='ethernet settings',
                      port_names=[port1.name, port3.name],
                      speed='speed_1_gbps',
                      media='copper',
                      promiscuous=False,
                      mtu=1500,
                      auto_negotiate=True)
    uhd = Layer1(name='uhd settings',
                 port_names=[port2.name],
                 speed='speed_100_gbps',
                 ieee_media_defaults=True,
                 auto_negotiate=False,
                 auto_negotiation=AutoNegotiation(link_training=False,
                                                  rs_fec=False))
    config = Config(ports=[port1, port2, port3], layer1=[ethernet, uhd])
    api.set_state(State(ConfigState(config=config, state='set')))


if __name__ == '__main__':
    pytest.main(['-s', __file__])

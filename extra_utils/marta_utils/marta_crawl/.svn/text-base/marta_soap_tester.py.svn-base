#!/usr/bin/python

from suds.client import Client

def get_update(input):
    """
    Returns the bus locations for a single route
    @params input - an integer representing the route number
    """
    
    url = 'http://developer.itsmarta.com/BRDWebService/BRDService.asmx?WSDL'
    
    c = Client(url)
    auth_header = c.factory.create('AuthHeader')
    auth_header.UserName = "ridecellbri"
    auth_header.Password = "jk8GKTY"
    c.set_options(soapheaders=auth_header)
    dataset = c.service.GetBRD(input).NewDataSet
    try:
        tables = dataset.Table
    except:
        return
    print len(tables)
    if len(tables) > 0:
        for table in tables:
            print table
            print '\n'

    return 

if __name__ == '__main__':
    """
    This function allows you to test for the vehicle locations at one or multiple routes.
    It is used for debugging purposes
    """
#    for i in range(0,400):
#        get_update(i)
#        print i
     get_update(5)

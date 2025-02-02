from hermes import models 

def insert_gateway_values(file_path):
    """
    this function loads the gateways into the database
    @param string file_path : file path to the txt file
    """
    fp = open(file_path)
    line = fp.readline()
    values_str = '("%s","%s","%s","%s"),' 
   
    cnt = 0
    while line:
        line = fp.readline()
        if line:
            cnt += 1
            line = line.strip("\r\n").replace('"', '').split(",")
            print line
            new_gw = models.Gateway.objects.create(description = line[0], lat = line[1], lng = line[2], gateway_id = line[3])
            new_gw.save()
           

def main():
    """
    main function for inserting gateways
    """
    insert_gateway_values("hermes/bin/gateways.txt")
    return


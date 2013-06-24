/* index.js

This file is main javascript file for the NITS simulator.

It's purpose is to pass commands from the end user to the Python views.

v0.1 - index.js acts as a state machine to continually check for passengers and insert passenger trips
in the Python views.

*/

//Global Variables
//TODO: identify which of these can be moved to a central confiuration file
var seconds = 0; //The number of seconds into the simulation.
var master_interval = false;
var INITIALIZING = true;
var GEN_PASSENGERS = false; //If true, we are waiting for Python to return from Generating Passengers
var READY_TO_INS_TRIPS = false; //If true, we have finished generating passengers and are ready to insert trips into the system
var INS_TRIPS = false; //If true, we are waiting for Python to return from inserting trips into the system
var SAVE_DATA = false; //if ture, we are saving data
var WAITING_FOR_SAVE = false;
var simulation_code; //Each simulation gets a unique simulation code
var simulation_length; //How long the simulation will be run in seconds
var passengers_per_second = .05; //For random passenger generation mode, this is the rate that passengers are make trip requests
var passenger_count;
var ready_trips;

/*initialize_simulation_data
This function deletes the old bus, gateway, and passenger data from previous simulations and recreates a fresh set of data for the current simulation. It also sets the simulation_code global variable.
*/
function initialize_simulation_data(){
    var html_data = $('#infoWindow').html(); 
    $('#infoWindow').html('Clearing Old Data...<br>' + html_data);
    $.ajaxSetup({async:false});
    $.post('/initialize_simulation_data/',
	   function(data){
	       var message = $.parseJSON(data);
	       simulation_code = message.simulation_code
	       INITIALIZING = false;
	       html_data = $('#infoWindow').html();
	       simulation_length = +message['simulation_length'];
	       $('#infoWindow').html('Finished Clearing Old Data, simulation code is: ' + message.simulation_code + '<br>' + html_data);
	       }
	  );
}


/*generate_passengers
This function takes returns a set of passengers requesting trips at a particular second in the simulation
@param
second: the current time into the simulation.  used to pull passengers from survey data
passengers_per_second: the rate at which passengers arrive, it is used when generating random sample data
simulation_code: future feature that will allow the database to maintain a total count of passengers across multiple simulations
@return
passenger_count: the number of passengers requesting trips at this second
second: the simulation second
ready_trips: the number of trips that are ready to inserted
*/
function generate_passengers(passengers_per_second, simulation_code, second){
    var passenger_count;
    console.log('waiting to generate passengers...');
    GEN_PASSENGERS = true;
    $.ajaxSetup({async:true});
    $.post('/generate_passengers/', {passengers_per_second:passengers_per_second, simulation_code:simulation_code, second:second},
	   function(data){
	       var html_data = $('#infoWindow').html(); 
	       var message = $.parseJSON(data);
	       passenger_count = message['passengers'];
	       seconds = message['second'];
	       ready_trips = message['ready_trips'];
	       GEN_PASSENGERS = false;
	       READY_TO_INS_TRIPS = true;
	   }
	  );
    console.log('passenger generation complete.');
    return [passenger_count, seconds, ready_trips]
}

/*insert_trips
This function takes in a second and inserts all the trips that are available to be inserted at that second.
@param
trip_id: an array of trips to be inserted
@return
opt_rte: the optimal route TODO:what is this doing now
*/
function insert_trips(trip_id){
    INS_TRIPS = true;
    var opt_rte;
    var locations;
    var flexbus_id;
    var home;
    var html_data = $('#infoWindow').html(); 
    console.log(trip_id);
    console.log(READY_TO_INS_TRIPS);
    var trip_ids;
    trip_ids = JSON.stringify(trip_id);
    console.log(trip_ids);
    $('#infoWindow').html('Current Time is ' + seconds + ' seconds.<br>' + html_data);   
    console.log('Inserting trips at time ' + seconds);
    $.ajaxSetup({async:true});
    $.post('/insert_trip/', {"second":seconds, "trip_ids":trip_ids},
	   function(data){
	       seconds = seconds + 1; // finished with inserting passengers, increment by one second
	       INS_TRIPS = false;
	   }
	  );
    return;
}

/*save_data
After the simulation is done, dump the database.
*/
function save_data(){

    if(WAITING_FOR_SAVE){
	save_data_status();
    }
    else{
	WAITING_FOR_SAVE = true;
    $.ajaxSetup({async:true});
    $.post('/save_data/', {},
	   function(data){
	       var message = $.parseJSON(data);
	       result = message['result'];
	       if(result){
		   console.log('Done without a timeout');
	       }
	   }
	  );
    return;
    }
}

/*save_data
After calling save data, sometimes the connection resets.  This checks to see if saving data is finished and kicks off the next iteration.
*/
function save_data_status(){


    WAITING_FOR_SAVE = true;
    $.ajaxSetup({async:true});
    $.get('/save_data_status/', {simulation_code:simulation_code},
	   function(data){
	       var message = $.parseJSON(data);
	       result = message['result'];
	       if(result){
		   SAVE_DATA = false;
		   WAITING_FOR_SAVE = false;
		   initialize();
	       }
	       else{
		   console.log('Still waiting for data to be saved. STATUS: FALSE');
	       }
	   }
	  );
    return;
    
}



/*master
This the main state machine controller for the NITS simulator.  Eventually this can be used to provide more indepth control to the end user. (Such as stopping/starting the simulation on command.)  A state machine type of system is used to get around the asynchronous nature of javascript/http calls  
This function looks at three variables representing the state of the system.
GEN_PASSENGERS: if true we are waiting for the python views to return a set of passengers
READY_TO_INS_TRIPS: if true we have a set of passengers/trips that are ready to be inserted into the system
INS_TRIPS: we are waiting for the python code to finish inserting trips
TODO: Consider creating a single state variable instead of using three.
*/
function master(){

    console.log('STATES------------------  ');
    console.log('INITIALIZING:  ' + INITIALIZING);
    console.log('GEN_PASSENGERS:  ' + GEN_PASSENGERS);
    console.log('READY_TO_INS_TRIPS:  ' + READY_TO_INS_TRIPS);
    console.log('INS_TRIPS:  ' + INS_TRIPS);
    console.log('SAVE_DATA:  ' + SAVE_DATA);

    var last_time = false;
    if (seconds > simulation_length && SAVE_DATA == false){
	last_time = true;
	
	var html_data = $('#infoWindow').html(); 
	$('#infoWindow').html('This is the last time that the script will run.  The simulation is over...<br>' + html_data);  
	SAVE_DATA = true;
    }

    if(GEN_PASSENGERS) 
	console.log('Generating passengers...waiting...');
    else{
	if(SAVE_DATA){
	    save_data(); }
	else{
	if(READY_TO_INS_TRIPS){
	    READY_TO_INS_TRIPS = false;
	    insert_trips(ready_trips);
	    console.log('Calling inserting trips');
	}
	else{
	    if(INS_TRIPS)
		console.log('Inserting Trips...waiting...');
	    else{
		ready_trips = [];
		console.log('done inserting trips.  Ready to move on to the next second');
		if(last_time){
		   var html_data = $('#infoWindow').html(); 
		    $('#infoWindow').html('Saving the data!<br>' + html_data);  
                   console.log('these passengers will never be inserted');
		    
		}
		else if(!INITIALIZING){
		    generate_passengers(passengers_per_second, simulation_code, seconds);
		}
	    }
   
	}
	}
    }
}


/* Main Control for the NITS index.js
This is what kicks off the state machine
initialize_simulation_data removes any data from the previous iteration and creates a fresh set, 
and the next line sets an interval that checks the state every 100 milliseconds and performs the appropriate action
*/
function initialize(){
    seconds = 0;
    INITIALIZING = true;
    SAVE_DATA = false;
    GEN_PASSENGERS = false; //If true, we are waiting for Python to return from Generating Passengers
    READY_TO_INS_TRIPS = false; //If true, we have finished generating passengers and are ready to insert trips into the system
    INS_TRIPS = false; //If true, we are waiting for Python to return from inserting trips into the system
    
    initialize_simulation_data();
    if(master_interval == false){
	master_interval = setInterval(function(){master()},1000);}
}



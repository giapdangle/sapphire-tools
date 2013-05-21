
#include "sapphire.h"

#include "app.h"

#include "init.h"

void main( void ) __attribute__ ((noreturn));

__attribute__ ((section (".fwinfo"))) fw_info_t fw_info;


void main( void ){      
        
    if( sapphire_i8_init() == 0 ){
        
        app_v_init();
    }
    
	sapphire_run();
	
	// should never get here:
	for(;;);
}   



#include "sapphire.h"

#include "app.h"
	


PT_THREAD( app_thread( pt_t *pt, void *state ) )
{       	
PT_BEGIN( pt );  


PT_END( pt );	
}


void app_v_init( void ){

    thread_t_create( app_thread,
                     PSTR("app"),
                     0,
                     0 );
}


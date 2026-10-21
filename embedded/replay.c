#include "engine_guard.h"
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <stdlib.h>
#include <math.h>
/* Text I/O is host harness only; embedded inference has no I/O or allocation. */
int main(int argc,char **argv){
    EgState state; EgOutput o; float u[6],p; int n,i; volatile float sink=0;
    eg_init(&state);
    if(argc>1 && strcmp(argv[1],"--selftest")==0){
        float test[6]={0.01f,150,105000,10,300,0.5f};
        test[0]=NAN;o=eg_step(&state,test,50000);if(o.status!=2)return 3;
        test[0]=0.01f;test[1]=0;o=eg_step(&state,test,50000);if(o.status!=2)return 4;
        test[1]=150;o=eg_step(&state,test,NAN);if(o.status!=2)return 5;
        test[0]=1;o=eg_step(&state,test,50000);if(o.status!=1)return 6;
        test[0]=0.01f;o=eg_step(&state,test,50000);if(o.status!=1)return 10;
        o=eg_step(&state,test,50000);if(o.status!=0)return 11;
        test[0]=0.01f;eg_init(&state);o=eg_step(&state,test,50000);p=o.pressure_pa;
        for(i=0;i<250;i++){o=eg_step(&state,test,p);if(o.alarm)return 7;}
        for(i=0;i<250;i++)o=eg_step(&state,test,p+20000);
        if(!o.alarm)return 8;
        eg_init(&state);o=eg_step(&state,test,p);if(o.alarm)return 9;
        puts("C defensive input, fallback, sustained-bias, and reset checks passed");return 0;
    }
    if(argc>1 && strcmp(argv[1],"--benchmark")==0){
        const float nominal[6]={0.01f,150,105000,10,300,0.5f};
        clock_t start; double elapsed; const int count=1000000;
        for(i=0;i<10000;i++){o=eg_step(&state,nominal,50000);sink+=o.pressure_pa;}
        start=clock();
        for(i=0;i<count;i++){o=eg_step(&state,nominal,50000);sink+=o.pressure_pa;}
        elapsed=(double)(clock()-start)/CLOCKS_PER_SEC;
        printf("{\"calls\":%d,\"elapsed_s\":%.9f,\"mean_us\":%.6f,\"state_bytes\":%lu}\n",count,elapsed,elapsed*1e6/count,(unsigned long)sizeof(state));
        return sink==0;
    }
    while((n=scanf("%f %f %f %f %f %f %f",&u[0],&u[1],&u[2],&u[3],&u[4],&u[5],&p))==7){
        o=eg_step(&state,u,p);
        printf("%.8g %.8g %u %u\n",o.pressure_pa,o.residual_pa,o.status,o.alarm);
        fflush(stdout); /* Also support the paced, one-sample-at-a-time host runner. */
    }
    return n==EOF?0:2;
}

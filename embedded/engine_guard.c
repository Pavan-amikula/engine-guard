#include "engine_guard.h"
#include "model_data.h"
#include <math.h>
#include <string.h>
static float limit(float x,float lo,float hi){return fminf(hi,fmaxf(lo,x));}
void eg_init(EgState *s){memset(s,0,sizeof(*s));}
float eg_predict(const float x[13]){
    float a[EG_H1], b[EG_H2], v, y;
    int i,j;
    for(j=0;j<EG_H1;j++){
        v=B1[j];
        for(i=0;i<13;i++)v+=((x[i]-XM[i])/XS[i])*(float)W1[i*EG_H1+j]*S1;
        a[j]=fmaxf(0,v);
    }
    for(j=0;j<EG_H2;j++){
        v=B2[j];
        for(i=0;i<EG_H1;i++)v+=a[i]*(float)W2[i*EG_H2+j]*S2;
        b[j]=fmaxf(0,v);
    }
    y=B3[0];
    for(i=0;i<EG_H2;i++)y+=b[i]*(float)W3[i]*S3;
    return y*YS+YM+PHYS_A*x[12]+PHYS_B;
}
EgOutput eg_step(EgState *s,const float u[6],float measured){
    EgOutput o={0,0,0,0}; float x[13],base; int i;
    for(i=0;i<6;i++){
        if(!isfinite(u[i])){o.status=2;eg_init(s);return o;}
    }
    if(u[0]<0 || u[1]<=0 || u[2]<=0 || u[4]<=0){o.status=2;eg_init(s);return o;}
    x[12]=u[0]*u[4]/u[1]; base=limit(PHYS_A*x[12]+PHYS_B,10000,250000);
    for(i=0;i<6;i++){
        x[i]=u[i];x[i+6]=s->initialized?s->previous[i]:u[i];
        if(u[i]<LO[i] || u[i]>HI[i] || x[i+6]<LO[i] || x[i+6]>HI[i])o.status=1;
        s->previous[i]=u[i];
    }
    s->initialized=1;
    o.pressure_pa=o.status?base:limit(eg_predict(x),10000,250000);
    if(!isfinite(measured) || measured<10000 || measured>250000){o.status=2;s->filtered=0;s->count=0;return o;}
    o.residual_pa=measured-o.pressure_pa;
    if(o.status){s->filtered=0;s->count=0;return o;}
    s->filtered=0.95f*s->filtered+0.05f*o.residual_pa;
    if(fabsf(s->filtered)>ALARM_THRESHOLD){if(s->count<10)s->count++;}else{s->count=0;}
    o.alarm=(s->count>=10)?1:0;
    return o;
}

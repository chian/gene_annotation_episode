#include "tld-logsum.h"

#include <math.h>
#include <float.h>

#define SCALE 1000.0F
#define LOGSUM_SIZE 16000

static float logsum_lookup[LOGSUM_SIZE];

void init_logsum()
{
        static int called = 0;
        int i = 0;
        if(!called){
                called = 1;
                for(i = 0; i < LOGSUM_SIZE;i++){
                        logsum_lookup[i] = logf(1.0F + expf((float) -i / SCALE));
                }
        }
}

float logsum(const float a,const float b)
{
        register const float max = MACRO_MAX(a, b);
        register const float min = MACRO_MIN(a, b);

        if(  TLSAFE_EQ(min, -INFINITY)){
                return max;
        }
        if( (max-min) >= 15.7F){
                return max;
        }
        return  max+ logsum_lookup[(int)((max-min)*SCALE)];
}

float prob2scaledprob(float p)
{
        float r = 0.0F;
        if( TLSAFE_EQ(p, 0.0F)){
                r = -INFINITY;
        }else{
                r = logf(p);
        }
        return r;
}

float scaledprob2prob(float p)
{
        float r = 0.0F;
        if( TLSAFE_EQ(p, -INFINITY)){
                r = 0.0F;
        }else{
                r = expf(p);
        }
        return r;
}

int nearly_equal_float(float a, float b)
{
        const float min = FLT_MIN;
        float absa = fabsf(a);
        float absb = fabsf(b);
        float d = fabsf(a-b);
        int ret = 0;
        if(a == b){
                ret = 1;
        }else if (a == 0.0F || b == 0 || (absa + absb < min)){
                ret =  d < (FLT_EPSILON * min);
        }else{
                ret =  d / MACRO_MIN((absa+absb), min) < FLT_EPSILON;
        }
        return ret;
}



int nearly_equal_double(double a, double b)
{
        const double min = DBL_MIN;
        double absa = fabs(a);
        double absb = fabs(b);
        double d = fabs(a-b);
        int ret = 0;
        if(a == b){
                ret = 1;
        }else if (a == 0.0 || b == 0 || (absa + absb < min)){
                ret = d < (DBL_EPSILON * min);
        }else{
                ret = d / MACRO_MIN((absa+absb), min) < DBL_EPSILON;
        }
        return ret;
}

#ifndef TLD_LOGSUM_H
#define TLD_LOGSUM_H

#include "../core/tld-core.h"

tld_external int nearly_equal_float(float a, float b);
tld_external int nearly_equal_double(double a, double b);

#define TLSAFE_EQ(X,Y) _Generic((X),                        \
                                float: nearly_equal_float,  \
                                double: nearly_equal_double \
                )(X,Y)


tld_external void init_logsum(void);
tld_external float logsum(const float a,const float b);
tld_external float prob2scaledprob(float p);
tld_external float scaledprob2prob(float p);

#endif

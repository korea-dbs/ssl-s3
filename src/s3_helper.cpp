#include <iostream>

#ifdef __cplusplus
extern "C" {
#endif
    void myCppFunction() {
        std::cout << "Hello from C++ function!" << std::endl;
    }
#ifdef __cplusplus
}
#endif


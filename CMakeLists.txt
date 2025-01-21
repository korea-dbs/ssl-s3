cmake_minimum_required(VERSION 3.10)

# Project name
project(sqlite3-cloud-s3)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# SQLite source directory
set(SQLITE_SOURCE_DIR ${CMAKE_SOURCE_DIR}/sqlite_src)
set(SQLITE_BUILD_DIR ${CMAKE_BINARY_DIR}/sqlite_bld)
file(MAKE_DIRECTORY ${SQLITE_BUILD_DIR})


# SQLite output library name
set(SQLITE_LIBRARY sqlite3)

# Custom command to configure SQLite
add_custom_command(
    OUTPUT ${SQLITE_BUILD_DIR}/Makefile
    COMMAND mkdir -p ${SQLITE_BUILD_DIR} && echo "Created build directory: ${SQLITE_BUILD_DIR}"
	COMMAND ${SQLITE_SOURCE_DIR}/configure --prefix=${SQLITE_BUILD_DIR} --disable-shared
    WORKING_DIRECTORY ${SQLITE_BUILD_DIR}
    COMMENT "Configuring SQLite"
)

# Custom command to build SQLite
add_custom_command(
    OUTPUT ${SQLITE_BUILD_DIR}/.libs/lib${SQLITE_LIBRARY}.a
    COMMAND make -j
    WORKING_DIRECTORY ${SQLITE_BUILD_DIR}
    DEPENDS ${SQLITE_BUILD_DIR}/Makefile
    COMMENT "Building SQLite library"
)

# Add a custom target for SQLite
add_custom_target(
    sqlite3_target
    DEPENDS ${SQLITE_BUILD_DIR}/.libs/lib${SQLITE_LIBRARY}.a
)

# Find AWS SDK for C++
find_package(AWSSDK REQUIRED COMPONENTS s3)

# Add main project executable
add_executable(${PROJECT_NAME}
    src/main.cpp
	src/s3_wrapper.cpp
)

include_directories(${SQLITE_SOURCE_DIR}/include)
include_directories(${CMAKE_SOURCE_DIR}/include)


set(SDK_INSTALL_LIB_DIR "/sdk-install/lib")
set(SDK_INSTALL_INCLUDE_DIR "/sdk-install/include")
include_directories(${SDK_INSTALL_INCLUDE_DIR})


link_directories(${SDK_INSTALL_LIB_DIR})
set(AWS_SDK_LIBS
    aws-cpp-sdk-core
    aws-cpp-sdk-s3
)

# Link SQLite library to the main project
target_link_libraries(${PROJECT_NAME} PRIVATE ${SQLITE_BUILD_DIR}/.libs/lib${SQLITE_LIBRARY}.a -lpthread -ldl
		${AWS_SDK_LIBS}
#		-laws-cpp-sdk-s3 -laws-cpp-sdk-core
		)

# Ensure SQLite is built before the main project
add_dependencies(${PROJECT_NAME} sqlite3_target)

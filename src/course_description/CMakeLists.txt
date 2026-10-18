cmake_minimum_required(VERSION 3.10)
project(course_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY urdf launch rviz
        DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/test/test_description.py")
    ament_add_pytest_test(test_description test/test_description.py
        APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
  endif()
endif()

ament_package()
cmake_minimum_required(VERSION 3.10)
project(course_simulation)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(DIRECTORY launch config models worlds
        DESTINATION share/${PROJECT_NAME})

install(PROGRAMS
        scripts/ackermann_adapter.py
        scripts/odom_adapter.py
        scripts/test_drive_source.py
        DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(test_kinematics test/test_kinematics.py
      APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
  ament_add_pytest_test(test_bridge_config test/test_bridge_config.py
      APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
  ament_add_pytest_test(test_model test/test_model.py
      APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
endif()

ament_package()

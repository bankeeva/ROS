cmake_minimum_required(VERSION 3.10)
project(localization_case)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch config
        DESTINATION share/${PROJECT_NAME})

install(PROGRAMS scripts/localization_metrics.py
        DESTINATION lib/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_pytest_test(test_config test/test_config.py
      APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
  ament_add_pytest_test(test_launch test/test_launch.py
      APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
  ament_add_pytest_test(test_metrics test/test_metrics.py
      APPEND_ENV PYTHONPATH=${CMAKE_CURRENT_SOURCE_DIR})
endif()

ament_package()

 - Try to use parametrized tests where possible to reduce code 
duplication and improve test coverage.
 - Follow the existing code style and conventions used in the project to maintain
 - Don't mock db sessions
 - Follow the same logic in tests
 - Use polyfactory for creating test data where applicable
 - All factories should be in the all_factories folder
 - Use factory_creators, factory_getters and factory_updaters for creating, 
getting and updating test data in test. If we don't have such functions yet, create them
 - Try to compare results of functions as full objects. Don't compare field by field unless it's necessary
 - Don't add imports inside functions
 - Check the usage of variables in tests
 - Always check response details when testing API responses when we have an error

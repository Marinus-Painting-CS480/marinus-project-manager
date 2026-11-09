-- Let the app user create and drop the throwaway database Django uses for tests.
GRANT ALL PRIVILEGES ON `test_marinus`.* TO 'marinus'@'%';
FLUSH PRIVILEGES;

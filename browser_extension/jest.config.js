module.exports = {
  preset: 'jest-puppeteer',
  testMatch: ['**/tests/**/*.test.js'], // Look for test files in a 'tests' subdirectory
  setupFilesAfterEnv: ['./jest.setup.js'], // Optional: for global setup after environment is ready
}; 
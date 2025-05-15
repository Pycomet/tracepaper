// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock global fetch for all tests
global.fetch = jest.fn();

// You can also mock other global objects here if needed, for example:
// global.window.electronAPI = {
//   invoke: jest.fn(),
//   send: jest.fn(),
//   on: jest.fn(() => () => {}), // Mock 'on' to return a cleanup function
// }; 
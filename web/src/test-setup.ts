// Jest setup: register @testing-library/jest-dom DOM matchers
// (toBeInTheDocument, etc.) for React component tests under jsdom.
import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'node:util';

// jsdom 未实现 TextEncoder/TextDecoder,部分依赖(iobuffer 等)在模块加载期即实例化,
// 不 polyfill 会在 import 阶段直接抛错
const globalScope = globalThis as Record<string, unknown>;
if (typeof globalScope.TextEncoder === 'undefined') globalScope.TextEncoder = TextEncoder;
if (typeof globalScope.TextDecoder === 'undefined') globalScope.TextDecoder = TextDecoder;

// Ant Design Drawer/Grid 依赖 window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// jsdom 对 ::-webkit-scrollbar 等伪元素的 getComputedStyle 抛 "not implemented"，
// Ant Design Drawer 测量滚动条时会触发。返回空对象避免测试噪音。
const originalGetComputedStyle = window.getComputedStyle;
Object.defineProperty(window, 'getComputedStyle', {
  writable: true,
  value: jest.fn((element: Element, pseudoElt?: string | null) => {
    if (pseudoElt) {
      return {
        width: '0px',
        height: '0px',
        paddingLeft: '0px',
        paddingRight: '0px',
      } as CSSStyleDeclaration;
    }
    return originalGetComputedStyle(element);
  }),
});

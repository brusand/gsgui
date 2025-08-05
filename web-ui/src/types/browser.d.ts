// Browser API type declarations for bookmarklet functionality

declare global {
  interface Window {
    chrome?: {
      bookmarks?: {
        create: (bookmark: { title: string; url: string }) => Promise<any>;
      };
    };
    sidebar?: {
      addPanel?: (title: string, url: string, category: string) => void;
    };
  }
}

export {};
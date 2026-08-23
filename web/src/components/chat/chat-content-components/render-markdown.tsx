import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import VisMermaid from './vis-mermaid';

const renderMarkdown = (content: string) => {
  return (
    <div className='uni-chat-markdown-container whitespace-normal'>
      <ReactMarkdown
        remarkPlugins={[remarkBreaks, remarkGfm]}
        rehypePlugins={[rehypeRaw, rehypeHighlight]}
        components={{
          // 块级代码:pre > code。mermaid 已由 code 组件渲染为独立组件，直接透传避免被 pre 包裹
          pre({ children }) {
            if (React.isValidElement(children) && children.type === VisMermaid) {
              return <>{children}</>;
            }
            return <pre className='whitespace-pre-wrap'>{children}</pre>;
          },
          // code 组件在 react-markdown v10 中不再收到 inline 属性，
          // 块级代码必带 language-xxx className，行内代码无 className，据此区分
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            if (match && match[1] === 'mermaid') {
              return <VisMermaid code={String(children)} />;
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

export default renderMarkdown;

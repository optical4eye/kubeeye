import React, { useEffect } from 'react';
import Prism from 'prismjs';
import 'prismjs/components/prism-yaml';
import 'prismjs/components/prism-bash';

interface CodeHighlighterProps {
  code: string;
  language: string;
}

const CodeHighlighter: React.FC<CodeHighlighterProps> = ({ code, language }) => {
  useEffect(() => {
    Prism.highlightAll();
  }, [code, language]);

  return (
    <pre className={`language-${language}`}>
      <code className={`language-${language}`}>{code}</code>
    </pre>
  );
};

export default CodeHighlighter;

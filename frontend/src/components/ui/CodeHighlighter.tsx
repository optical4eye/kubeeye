import React from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import customSyntaxStyle from './HelpTabs/syntaxStyles';

interface CodeHighlighterProps {
  code: string;
  language: string;
}

const CodeHighlighter: React.FC<CodeHighlighterProps> = ({ code, language }) => (
  <SyntaxHighlighter language={language} style={customSyntaxStyle}>
    {code}
  </SyntaxHighlighter>
);

export default CodeHighlighter;

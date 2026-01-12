// Custom syntax highlighter style matching the app theme
const customSyntaxStyle = {
  'code[class*="language-"]': {
    color: '#ff79c6',
    background: '#21222c',
    fontFamily: '"Inconsolata", "Monaco", "Consolas", monospace',
    fontSize: '14px',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
  },
  'pre[class*="language-"]': {
    color: '#f8f8f2',
    background: '#21222c',
    fontFamily: '"Inconsolata", "Monaco", "Consolas", monospace',
    fontSize: '14px',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: '1.5',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
    padding: '16px',
    margin: '0',
    overflow: 'auto',
    borderRadius: '4px',
    border: '1px solid #6272a4',
  },
  'pre[class*="language-"]::-moz-selection': {
    background: '#44475a',
  },
  'pre[class*="language-"] ::-moz-selection': {
    background: '#44475a',
  },
  'code[class*="language-"]::-moz-selection': {
    background: '#44475a',
  },
  'code[class*="language-"] ::-moz-selection': {
    background: '#44475a',
  },
  'pre[class*="language-"]::selection': {
    background: '#44475a',
  },
  'pre[class*="language-"] ::selection': {
    background: '#44475a',
  },
  'code[class*="language-"]::selection': {
    background: '#44475a',
  },
  'code[class*="language-"] ::selection': {
    background: '#44475a',
  },
  ':not(pre) > code[class*="language-"]': {
    background: '#21222c',
    padding: '0.1em',
    borderRadius: '0.3em',
    whiteSpace: 'normal',
  },
  comment: {
    color: '#cccccc',
  },
  prolog: {
    color: '#cccccc',
  },
  doctype: {
    color: '#cccccc',
  },
  cdata: {
    color: '#cccccc',
  },
  punctuation: {
    color: '#8b94b8',
  },
  property: {
    color: '#6366f1',
  },
  key: {
    color: '#6366f1',
  },
  tag: {
    color: '#6366f1',
  },
  constant: {
    color: '#ffb86c',
  },
  symbol: {
    color: '#ffb86c',
  },
  deleted: {
    color: '#ff5555',
  },
  boolean: {
    color: '#50fa7b',
  },
  number: {
    color: '#50fa7b',
  },
  selector: {
    color: '#ff79c6',
  },
  'attr-name': {
    color: '#ff79c6',
  },
  string: {
    color: '#f1fa8c',
  },
  char: {
    color: '#f1fa8c',
  },
  builtin: {
    color: '#ff79c6',
  },
  inserted: {
    color: '#50fa7b',
  },
  operator: {
    color: '#8b94b8',
  },
  entity: {
    color: '#6366f1',
    cursor: 'help',
  },
  url: {
    color: '#6366f1',
  },
  '.language-css .token.string': {
    color: '#f1fa8c',
  },
  '.style .token.string': {
    color: '#f1fa8c',
  },
  variable: {
    color: '#ffb86c',
  },
  atrule: {
    color: '#8be9fd',
  },
  'attr-value': {
    color: '#f1fa8c',
  },
  function: {
    color: '#ff79c6',
  },
  'class-name': {
    color: '#ff79c6',
  },
  keyword: {
    color: '#8be9fd',
  },
  regex: {
    color: '#50fa7b',
  },
  important: {
    color: '#ff5555',
    fontWeight: 'bold',
  },
  bold: {
    fontWeight: 'bold',
  },
  italic: {
    fontStyle: 'italic',
  },
};

export default customSyntaxStyle;

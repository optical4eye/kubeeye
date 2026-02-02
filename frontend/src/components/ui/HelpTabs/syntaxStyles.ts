// Custom syntax highlighter style matching the app theme
// Uses Ant Design CSS variables for theme-aware colors
const customSyntaxStyle = {
  'code[class*="language-"]': {
    color: 'var(--ant-color-primary)',
    background: 'var(--ant-color-bg-layout)',
    fontFamily: '"Inconsolata", "Monaco", "Consolas", monospace',
    fontSize: 'var(--ant-font-size-sm)',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: 'var(--ant-line-height)',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
  },
  'pre[class*="language-"]': {
    color: 'var(--ant-color-text)',
    background: 'var(--ant-color-bg-layout)',
    fontFamily: '"Inconsolata", "Monaco", "Consolas", monospace',
    fontSize: 'var(--ant-font-size-sm)',
    textAlign: 'left',
    whiteSpace: 'pre',
    wordSpacing: 'normal',
    wordBreak: 'normal',
    wordWrap: 'normal',
    lineHeight: 'var(--ant-line-height)',
    MozTabSize: '4',
    OTabSize: '4',
    tabSize: '4',
    WebkitHyphens: 'none',
    MozHyphens: 'none',
    msHyphens: 'none',
    hyphens: 'none',
    padding: 'var(--ant-padding-lg)',
    margin: '0',
    overflow: 'auto',
    borderRadius: 'var(--ant-border-radius-sm)',
    border: '1px solid var(--ant-color-border)',
  },
  'pre[class*="language-"]::-moz-selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  'pre[class*="language-"] ::-moz-selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  'code[class*="language-"]::-moz-selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  'code[class*="language-"] ::-moz-selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  'pre[class*="language-"]::selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  'pre[class*="language-"] ::selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  'code[class*="language-"]::selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  'code[class*="language-"] ::selection': {
    background: 'var(--ant-color-bg-spotlight)',
  },
  ':not(pre) > code[class*="language-"]': {
    background: 'var(--ant-color-bg-layout)',
    padding: '0.1em',
    borderRadius: '0.3em',
    whiteSpace: 'normal',
  },
  comment: {
    color: 'var(--ant-color-text-secondary)',
  },
  prolog: {
    color: 'var(--ant-color-text-secondary)',
  },
  doctype: {
    color: 'var(--ant-color-text-secondary)',
  },
  cdata: {
    color: 'var(--ant-color-text-secondary)',
  },
  punctuation: {
    color: 'var(--ant-color-text-tertiary)',
  },
  property: {
    color: 'var(--ant-color-primary)',
  },
  key: {
    color: 'var(--ant-color-primary)',
  },
  tag: {
    color: 'var(--ant-color-primary)',
  },
  constant: {
    color: 'var(--ant-color-warning)',
  },
  symbol: {
    color: 'var(--ant-color-warning)',
  },
  deleted: {
    color: 'var(--ant-color-error)',
  },
  boolean: {
    color: 'var(--ant-color-success)',
  },
  number: {
    color: 'var(--ant-color-success)',
  },
  selector: {
    color: 'var(--ant-color-primary)',
  },
  'attr-name': {
    color: 'var(--ant-color-primary)',
  },
  string: {
    color: 'var(--ant-color-info)',
  },
  char: {
    color: 'var(--ant-color-info)',
  },
  builtin: {
    color: 'var(--ant-color-primary)',
  },
  inserted: {
    color: 'var(--ant-color-success)',
  },
  operator: {
    color: 'var(--ant-color-text-tertiary)',
  },
  entity: {
    color: 'var(--ant-color-primary)',
    cursor: 'help',
  },
  url: {
    color: 'var(--ant-color-primary)',
  },
  '.language-css .token.string': {
    color: 'var(--ant-color-info)',
  },
  '.style .token.string': {
    color: 'var(--ant-color-info)',
  },
  variable: {
    color: 'var(--ant-color-warning)',
  },
  atrule: {
    color: 'var(--ant-color-info)',
  },
  'attr-value': {
    color: 'var(--ant-color-info)',
  },
  function: {
    color: 'var(--ant-color-primary)',
  },
  'class-name': {
    color: 'var(--ant-color-primary)',
  },
  keyword: {
    color: 'var(--ant-color-info)',
  },
  regex: {
    color: 'var(--ant-color-success)',
  },
  important: {
    color: 'var(--ant-color-error)',
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

import { useState } from 'react';

interface CopyButtonProps {
  text: string;
  label?: string;
}

export default function CopyButton({ text, label = 'Copy' }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="px-3 py-1 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-md transition-colors"
      aria-label={`${label} to clipboard`}
    >
      {copied ? 'Copied!' : label}
    </button>
  );
}

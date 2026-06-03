'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Key, CheckCircle2, XCircle, Loader2, CreditCard } from 'lucide-react';
import { setLicenseKey, clearLicenseKey, getLicenseKey, hasLicenseKey } from '@/lib/analysisStore';

interface LicenseKeyManagerProps {
  onKeyChange?: (hasKey: boolean) => void;
  compact?: boolean;
}

export default function LicenseKeyManager({ onKeyChange, compact = false }: LicenseKeyManagerProps) {
  const t = useTranslations('license');
  const tPaywall = useTranslations('paywall');

  const [currentKey, setCurrentKey] = useState<string>(getLicenseKey() || '');
  const [inputValue, setInputValue] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const hasKey = hasLicenseKey();

  const handleSave = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) {
      setMessage({ type: 'error', text: tPaywall('enterKeyError') || 'Please enter a license key' });
      return;
    }

    setIsSaving(true);
    try {
      setLicenseKey(trimmed);
      setCurrentKey(trimmed);
      setInputValue('');
      setMessage({ type: 'success', text: t('saved') || 'License key saved. You can now analyze contracts.' });
      onKeyChange?.(true);
    } finally {
      setIsSaving(false);
      // Clear message after a bit
      setTimeout(() => setMessage(null), 3000);
    }
  };

  const handleClear = () => {
    clearLicenseKey();
    setCurrentKey('');
    setInputValue('');
    setMessage({ type: 'success', text: t('cleared') || 'License key removed.' });
    onKeyChange?.(false);
    setTimeout(() => setMessage(null), 2000);
  };

  if (compact) {
    return (
      <div className="text-xs text-gray-400 flex items-center gap-2">
        <Key className="w-3 h-3" />
        {hasKey ? t('hasKey') || 'Access key active' : tPaywall('noKey') || 'No access key'}
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl p-4 border-gray-800/50">
      <div className="flex items-center gap-2 mb-3">
        <Key className="w-4 h-4 text-blue-400" />
        <h3 className="font-medium text-gray-200">{t('title') || 'Access Key'}</h3>
      </div>

      {hasKey && currentKey ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-green-400">
            <CheckCircle2 className="w-4 h-4" />
            {t('active') || 'Access key active'}
          </div>
          <div className="font-mono text-xs bg-gray-950/60 rounded px-3 py-2 text-gray-400 break-all">
            {currentKey.slice(0, 4)}••••••••••••{currentKey.slice(-4)}
          </div>
          <button
            onClick={handleClear}
            className="text-xs text-red-400 hover:text-red-300 underline"
          >
            {t('clear') || 'Remove key'}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">
            {tPaywall('enterKeyHelp') || 'Enter a license key you received after purchase or via email.'}
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={tPaywall('keyPlaceholder') || 'POLAR-XXXX-YYYY-...'}
              className="flex-1 bg-gray-950 border border-gray-800 rounded-lg px-3 py-2 text-sm font-mono placeholder:text-gray-600 focus:outline-none focus:border-blue-700"
            />
            <button
              onClick={handleSave}
              disabled={isSaving || !inputValue.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-400 text-white text-sm rounded-lg flex items-center gap-2"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Key className="w-4 h-4" />}
              {t('save') || 'Save'}
            </button>
          </div>
        </div>
      )}

      {message && (
        <div className={`mt-3 text-xs flex items-center gap-1.5 ${message.type === 'success' ? 'text-green-400' : 'text-red-400'}`}>
          {message.type === 'success' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
          {message.text}
        </div>
      )}

      {!hasKey && (
        <div className="mt-4 pt-3 border-t border-gray-800">
          <a
            href="#buy"
            className="inline-flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300"
          >
            <CreditCard className="w-4 h-4" />
            {tPaywall('buyCta') || 'Buy an access pass instead'}
          </a>
        </div>
      )}
    </div>
  );
}

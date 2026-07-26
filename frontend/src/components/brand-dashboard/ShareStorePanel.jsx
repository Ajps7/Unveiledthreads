import { QRCodeCanvas } from 'qrcode.react';
import { Button } from '../ui/button';
import { Share2, Copy, Download, QrCode } from 'lucide-react';

/**
 * Vanity URL + downloadable QR panel for the brand dashboard.
 * Renders nothing when brand has no slug yet.
 */
export function ShareStorePanel({ brandData }) {
  if (!brandData?.slug) return null;

  const storeUrl = `${window.location.origin}/@${brandData.slug}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(storeUrl);
      alert('Store link copied to clipboard!');
    } catch {
      window.prompt('Copy this link:', storeUrl);
    }
  };

  const handleDownloadQR = () => {
    const canvas = document.querySelector('[data-testid="store-qr-canvas"] canvas');
    if (!canvas) return;
    const url = canvas.toDataURL('image/png');
    const a = document.createElement('a');
    a.href = url;
    a.download = `unveiledthreads-${brandData.slug}-qr.png`;
    a.click();
  };

  return (
    <div className="mb-12 border border-white/10 bg-[#0A0A0A] p-6" data-testid="store-share-panel">
      <div className="flex items-start gap-4">
        <Share2 className="w-8 h-8 text-[#39FF14] flex-shrink-0" />
        <div className="flex-1">
          <h3 className="text-xl font-bold text-white mb-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            YOUR STORE LINK
          </h3>
          <p className="text-[#9CA3AF] mb-4 text-sm">
            Share this link in your Instagram bio, TikTok profile, email signature, or printed cards.
          </p>
          <div className="flex flex-col lg:flex-row gap-4 items-start">
            <div className="flex-1 w-full">
              <div
                className="flex items-center gap-2 bg-[#0F0F0F] border border-white/10 p-3 font-mono text-sm text-white overflow-x-auto"
                data-testid="store-url-display"
              >
                {storeUrl}
              </div>
              <div className="flex gap-2 mt-3">
                <Button className="btn-primary text-sm" onClick={handleCopy} data-testid="copy-store-link-button">
                  <Copy className="w-4 h-4 mr-2" />
                  Copy Link
                </Button>
                <Button
                  className="btn-secondary text-sm"
                  onClick={handleDownloadQR}
                  data-testid="download-qr-button"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Download QR
                </Button>
              </div>
              <p className="text-xs text-[#9CA3AF] mt-3 flex items-start gap-1">
                <QrCode className="w-3 h-3 mt-0.5 flex-shrink-0" />
                Need to change your handle? Drop us a line at hello@unveiledthreads.co.uk.
              </p>
            </div>
            <div className="bg-white p-3" data-testid="store-qr-canvas">
              <QRCodeCanvas value={storeUrl} size={140} bgColor="#FFFFFF" fgColor="#000000" level="M" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { EditListingDialog } from '../components/my-listings/EditListingDialog';
import { toast } from 'sonner';
import {
  ArrowLeft, Upload, FileText, Loader2, CheckCircle2, AlertTriangle, Package,
  Edit, Trash2, Rocket, ChevronRight, Info, X,
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ImportProducts() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [importResult, setImportResult] = useState(null);

  const [drafts, setDrafts] = useState([]);
  const [loadingDrafts, setLoadingDrafts] = useState(true);
  const [publishingAll, setPublishingAll] = useState(false);
  const [publishingIds, setPublishingIds] = useState(new Set());

  const [editProduct, setEditProduct] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);

  const fetchDrafts = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/products/my/drafts`, { withCredentials: true });
      setDrafts(res.data || []);
    } catch (e) {
      console.error('Failed to load drafts', e);
    } finally {
      setLoadingDrafts(false);
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    if (user.role !== 'brand' && user.role !== 'admin') { navigate('/apply'); return; }
    fetchDrafts();
  }, [user, authLoading, navigate, fetchDrafts]);

  const handleFileChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please choose a .csv file');
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      toast.error('CSV must be under 5MB');
      return;
    }
    setFile(f);
    setImportResult(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setImportResult(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await axios.post(`${API}/api/products/import/csv`, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImportResult(res.data);
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      toast.success(`Imported ${res.data.created} products as drafts`);
      fetchDrafts();
    } catch (e) {
      const detail = e?.response?.data?.detail || 'Import failed. Please try again.';
      toast.error(detail);
    } finally {
      setUploading(false);
    }
  };

  const openEdit = (product) => {
    setEditProduct(product);
    setEditForm({
      name: product.name || '',
      description: product.description || '',
      price: product.price?.toString() || '',
      category: product.category || 'accessories',
      sizes: product.sizes || [],
      images: product.images || [],
      stock: product.stock?.toString() || '0',
      shipping_cost: product.shipping_cost?.toString() || '3.99',
    });
  };

  const handleSaveEdit = async () => {
    if (!editProduct) return;
    setSaving(true);
    try {
      const payload = {
        ...editForm,
        price: parseFloat(editForm.price),
        stock: parseInt(editForm.stock, 10) || 0,
        shipping_cost: parseFloat(editForm.shipping_cost) || 0,
      };
      await axios.put(`${API}/api/products/${editProduct.id}`, payload, { withCredentials: true });
      toast.success('Draft updated');
      setEditProduct(null);
      fetchDrafts();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to update draft');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this draft? This can\u2019t be undone.')) return;
    try {
      await axios.delete(`${API}/api/products/${id}`, { withCredentials: true });
      toast.success('Draft deleted');
      fetchDrafts();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to delete');
    }
  };

  const handlePublish = async (id) => {
    setPublishingIds((s) => new Set(s).add(id));
    try {
      await axios.post(`${API}/api/products/${id}/publish`, {}, { withCredentials: true });
      toast.success('Published — your listing is live');
      fetchDrafts();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not publish this draft');
    } finally {
      setPublishingIds((s) => {
        const next = new Set(s);
        next.delete(id);
        return next;
      });
    }
  };

  const handlePublishAll = async () => {
    setPublishingAll(true);
    try {
      const res = await axios.post(`${API}/api/products/drafts/publish-all`, {}, { withCredentials: true });
      toast.success(`Published ${res.data.published} listings. ${res.data.skipped} still need attention.`);
      fetchDrafts();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Bulk publish failed');
    } finally {
      setPublishingAll(false);
    }
  };

  const validDraftCount = drafts.filter((d) => {
    return d.images?.length > 0 && d.moderation_status !== 'flagged' && d.moderation_status !== 'needs_review' && !d.missing_images;
  }).length;

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-8 h-8 text-[#39FF14] animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-6xl mx-auto px-6 md:px-12 py-8">
        <Link
          to="/brand/dashboard"
          className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors"
          data-testid="back-to-dashboard"
        >
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>

        {/* Title */}
        <div className="mb-8">
          <h1
            className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white mb-2"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="import-title"
          >
            IMPORT YOUR CATALOGUE
          </h1>
          <p className="text-sm text-[#9CA3AF] max-w-2xl">
            Upload a CSV exported from Shopify, Etsy, WooCommerce, Squarespace, or a generic
            catalogue export. Products land as reviewable drafts — nothing goes live until
            you publish each one and it clears image moderation.
          </p>
        </div>

        {/* Upload panel */}
        <div className="border border-white/10 bg-[#0A0A0A] p-6 md:p-8 mb-10">
          <div className="flex items-center gap-3 mb-4">
            <Upload className="w-5 h-5 text-[#39FF14]" />
            <h2 className="text-lg font-bold text-white uppercase tracking-wider" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Upload CSV
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="md:col-span-2">
              <label
                className="border-2 border-dashed border-white/20 bg-[#050505] p-6 flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-[#39FF14]/60 transition-colors"
                data-testid="csv-drop-zone"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,text/csv"
                  onChange={handleFileChange}
                  className="hidden"
                  data-testid="csv-file-input"
                />
                <FileText className="w-8 h-8 text-[#9CA3AF]" />
                {file ? (
                  <>
                    <p className="text-sm text-white font-medium" data-testid="selected-filename">{file.name}</p>
                    <p className="text-xs text-[#9CA3AF]">{(file.size / 1024).toFixed(1)} KB · click to choose a different file</p>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-white">Choose a CSV file</p>
                    <p className="text-xs text-[#9CA3AF]">Max 5MB · up to 200 products per file</p>
                  </>
                )}
              </label>
              <Button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="btn-primary w-full mt-4"
                data-testid="upload-csv-button"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Importing…
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" /> Import products
                  </>
                )}
              </Button>
            </div>

            <div className="border border-white/10 p-4 bg-[#050505]">
              <div className="flex items-center gap-2 mb-3">
                <Info className="w-4 h-4 text-[#39FF14]" />
                <p className="text-xs uppercase tracking-wider text-white font-bold">Supported columns</p>
              </div>
              <ul className="text-xs text-[#9CA3AF] space-y-1.5">
                <li>· <span className="text-white">Title / Name</span></li>
                <li>· <span className="text-white">Body (HTML) / Description</span></li>
                <li>· <span className="text-white">Variant Price / Price</span></li>
                <li>· <span className="text-white">Product Type / Category</span></li>
                <li>· <span className="text-white">Option1 Value / Size</span></li>
                <li>· <span className="text-white">Variant Inventory Qty / Stock</span></li>
                <li>· <span className="text-white">Image Src / Image URL</span></li>
              </ul>
              <p className="text-[10px] text-[#6B7280] mt-3">
                Column names are matched case-insensitively. Rows with the same Handle (or repeated
                title) are grouped into a single product with multiple sizes and images.
              </p>
            </div>
          </div>
        </div>

        {/* Import result */}
        {importResult && (
          <div className="border border-[#39FF14]/40 bg-[#39FF14]/5 p-6 mb-10" data-testid="import-result">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-6 h-6 text-[#39FF14]" />
                <div>
                  <p className="text-lg font-bold text-white" data-testid="import-summary-line">
                    {importResult.created} imported as drafts
                    {importResult.skipped > 0 && ` · ${importResult.skipped} skipped`}
                  </p>
                  <p className="text-xs text-[#9CA3AF]">Review each draft below, then publish.</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setImportResult(null)}
                className="text-[#9CA3AF] hover:text-white"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {importResult.errors?.length > 0 && (
              <div className="mt-4">
                <p className="text-xs uppercase tracking-wider text-yellow-300 font-bold mb-2">
                  Skipped rows
                </p>
                <div className="max-h-48 overflow-y-auto border border-white/10 bg-[#050505]">
                  <table className="w-full text-xs">
                    <thead className="bg-[#0A0A0A] sticky top-0">
                      <tr>
                        <th className="text-left px-3 py-2 text-[#9CA3AF]">Row</th>
                        <th className="text-left px-3 py-2 text-[#9CA3AF]">Product</th>
                        <th className="text-left px-3 py-2 text-[#9CA3AF]">Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {importResult.errors.map((e, i) => (
                        <tr key={i} className="border-t border-white/5">
                          <td className="px-3 py-2 text-white">{e.row ?? '—'}</td>
                          <td className="px-3 py-2 text-white">{e.name}</td>
                          <td className="px-3 py-2 text-[#9CA3AF]">{e.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {importResult.warnings?.length > 0 && (
              <details className="mt-4">
                <summary className="text-xs text-[#9CA3AF] cursor-pointer hover:text-white">
                  {importResult.warnings.length} draft(s) imported with warnings — review before publishing
                </summary>
                <div className="mt-2 max-h-48 overflow-y-auto border border-white/10 bg-[#050505] text-xs">
                  {importResult.warnings.map((w, i) => (
                    <div key={i} className="px-3 py-2 border-t border-white/5 first:border-t-0">
                      <p className="text-white font-medium">{w.name}</p>
                      <ul className="mt-1 text-[#9CA3AF] list-disc list-inside">
                        {w.warnings.map((msg, j) => <li key={j}>{msg}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}

        {/* Drafts section */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-lg font-bold text-white uppercase tracking-wider" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Drafts to review
            </h2>
            <p className="text-xs text-[#9CA3AF]">
              {drafts.length} draft{drafts.length === 1 ? '' : 's'} · {validDraftCount} ready to publish
            </p>
          </div>
          {drafts.length > 0 && (
            <Button
              onClick={handlePublishAll}
              disabled={publishingAll || validDraftCount === 0}
              className="btn-primary"
              data-testid="publish-all-button"
            >
              {publishingAll ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Publishing…</>
              ) : (
                <><Rocket className="w-4 h-4 mr-2" /> Publish all valid ({validDraftCount})</>
              )}
            </Button>
          )}
        </div>

        {loadingDrafts ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 text-[#39FF14] animate-spin" />
          </div>
        ) : drafts.length === 0 ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-12 text-center">
            <Package className="w-12 h-12 text-[#9CA3AF] mx-auto mb-3" />
            <p className="text-white font-bold mb-1">No drafts yet</p>
            <p className="text-xs text-[#9CA3AF]">Upload a CSV above to bring your catalogue in.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="drafts-grid">
            {drafts.map((d) => {
              const blockers = draftBlockers(d);
              const imgSrc = d.images?.[0]
                ? (d.images[0].startsWith('/api/') ? `${API}${d.images[0]}` : d.images[0])
                : null;
              const isPublishing = publishingIds.has(d.id);
              return (
                <div
                  key={d.id}
                  className="border border-white/10 bg-[#0A0A0A] overflow-hidden"
                  data-testid={`draft-${d.id}`}
                >
                  <div className="aspect-[4/3] bg-[#0F0F0F] relative">
                    {imgSrc ? (
                      <img src={imgSrc} alt={d.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">
                        <Package className="w-8 h-8" />
                      </div>
                    )}
                    <div className="absolute top-2 left-2">
                      <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                        Draft
                      </span>
                    </div>
                  </div>
                  <div className="p-4">
                    <h3 className="text-white font-medium mb-1 line-clamp-1">{d.name}</h3>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[#39FF14] font-bold">£{Number(d.price || 0).toFixed(2)}</span>
                      <span className="badge-category text-[10px]">{d.category}</span>
                    </div>
                    <p className="text-xs text-[#9CA3AF] mb-3">
                      {d.images?.length || 0} image{(d.images?.length || 0) === 1 ? '' : 's'} · {d.sizes?.length || 0} size{(d.sizes?.length || 0) === 1 ? '' : 's'} · stock {d.stock ?? 0}
                    </p>

                    {blockers.length > 0 && (
                      <div className="mb-3 border border-yellow-500/30 bg-yellow-500/5 p-2">
                        <div className="flex items-start gap-2">
                          <AlertTriangle className="w-3 h-3 text-yellow-300 flex-shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-[10px] uppercase tracking-wider text-yellow-300 font-bold mb-1">
                              Fix before publishing
                            </p>
                            <ul className="text-[11px] text-[#9CA3AF] space-y-0.5">
                              {blockers.map((b, i) => <li key={i}>· {b}</li>)}
                            </ul>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="flex gap-2">
                      <Button
                        className="btn-secondary flex-1 text-xs py-1"
                        onClick={() => openEdit(d)}
                        data-testid={`edit-draft-${d.id}`}
                      >
                        <Edit className="w-3 h-3 mr-1" /> Edit
                      </Button>
                      <Button
                        className="btn-primary flex-1 text-xs py-1"
                        disabled={blockers.length > 0 || isPublishing}
                        onClick={() => handlePublish(d.id)}
                        data-testid={`publish-draft-${d.id}`}
                      >
                        {isPublishing ? (
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        ) : (
                          <Rocket className="w-3 h-3 mr-1" />
                        )}
                        Publish
                      </Button>
                      <Button
                        variant="ghost"
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10 px-2"
                        onClick={() => handleDelete(d.id)}
                        data-testid={`delete-draft-${d.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {drafts.length > 0 && (
          <div className="mt-6">
            <Link to="/brand/products" className="text-xs text-[#39FF14] hover:underline inline-flex items-center gap-1">
              View published listings <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        )}
      </div>

      <EditListingDialog
        editProduct={editProduct}
        editForm={editForm}
        setEditForm={setEditForm}
        saving={saving}
        onSave={handleSaveEdit}
        onClose={() => setEditProduct(null)}
      />
    </div>
  );
}

/**
 * Client-side mirror of the backend's _draft_publish_blocker.
 * Kept in sync so the Publish button disables on the exact same criteria
 * the API enforces — no wasted round-trips + no false "publishable" hopes.
 */
function draftBlockers(d) {
  const out = [];
  if (!d.images || d.images.length === 0) out.push('Add at least one image');
  if (d.missing_images) out.push('Some images from the CSV couldn\u2019t be imported — replace them');
  if (d.moderation_status === 'flagged') out.push('Images were flagged — replace them');
  if (d.moderation_status === 'needs_review') out.push('Images pending admin review');
  if (!d.name || d.name.trim().length < 2) out.push('Product name is missing');
  if (!d.description || d.description.trim().length < 10) out.push('Description too short (min 10 chars)');
  if (!d.price || d.price <= 0) out.push('Price must be greater than £0');
  if (!d.sizes || d.sizes.length === 0) out.push('Add at least one size');
  if (!d.category) out.push('Category is missing');
  return out;
}

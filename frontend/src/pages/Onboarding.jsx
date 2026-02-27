import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { onboardMerchant, onboardSupplier, getCurrentUser } from "../api/api";
import "./Onboarding.css";

const MERCHANT_INIT = {
  name: "",
  business_type: "",
  contact_person: "",
  phone_number: "",
  email: "",
  avg_daily_sales: "",
  consistency: "",
  days_active: "",
};

const SUPPLIER_INIT = {
  name: "",
  contact_person: "",
  phone_number: "",
  email: "",
  product_category: "",
};

export default function Onboarding() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [role, setRole] = useState(null); // "merchant" | "supplier"
  const [merchantData, setMerchantData] = useState({ ...MERCHANT_INIT, email: user?.email || "" });
  const [supplierData, setSupplierData] = useState({ ...SUPPLIER_INIT, email: user?.email || "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Already onboarded — redirect
  if (user?.is_merchant) { navigate("/merchant", { replace: true }); return null; }
  if (user?.is_supplier) { navigate("/supplier", { replace: true }); return null; }

  const selectRole = (r) => {
    setRole(r);
    setStep(2);
    setError("");
  };

  const goBack = () => {
    setStep(1);
    setRole(null);
    setError("");
  };

  const updateField = (setter) => (field) => (e) => {
    setter((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      if (role === "merchant") {
        const payload = {
          ...merchantData,
          avg_daily_sales: Number(merchantData.avg_daily_sales),
          consistency: Number(merchantData.consistency),
          days_active: Number(merchantData.days_active),
        };
        await onboardMerchant(payload);
      } else {
        await onboardSupplier(supplierData);
      }

      // Refresh user so role flags update
      const { data: updated } = await getCurrentUser();
      setUser(updated);

      navigate(role === "merchant" ? "/merchant" : "/supplier", { replace: true });
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") setError(detail);
      else if (Array.isArray(detail)) setError(detail.map((d) => d.msg).join(". "));
      else setError("Onboarding failed. Please check your details and try again.");
    } finally {
      setLoading(false);
    }
  };

  const m = updateField(setMerchantData);
  const s = updateField(setSupplierData);

  return (
    <div className="onboard-page">
      <div className="onboard-card">
        {/* Step indicator */}
        <div className="onboard-steps">
          <div className={`step-dot ${step >= 1 ? "active" : ""} ${step > 1 ? "done" : ""}`}>
            {step > 1 ? "✓" : "1"}
          </div>
          <div className={`step-line ${step > 1 ? "active" : ""}`} />
          <div className={`step-dot ${step >= 2 ? "active" : ""}`}>2</div>
        </div>

        {/* ── Step 1: Role selection ─────────── */}
        {step === 1 && (
          <>
            <h2>Choose your role</h2>
            <p className="onboard-sub">
              Select how you'll use Lipwa Trust. You can only be onboarded once.
            </p>

            <div className="role-cards">
              <div
                className={`role-card ${role === "merchant" ? "selected" : ""}`}
                onClick={() => selectRole("merchant")}
              >
                <span className="role-icon">🏪</span>
                <div className="role-title">Merchant</div>
                <div className="role-desc">Apply for credit and manage your business financing</div>
              </div>

              <div
                className={`role-card ${role === "supplier" ? "selected" : ""}`}
                onClick={() => selectRole("supplier")}
              >
                <span className="role-icon">🏭</span>
                <div className="role-title">Supplier</div>
                <div className="role-desc">Supply goods to merchants and manage contracts</div>
              </div>
            </div>
          </>
        )}

        {/* ── Step 2: Role-specific form ────── */}
        {step === 2 && role === "merchant" && (
          <>
            <h2>Merchant details</h2>
            <p className="onboard-sub">Tell us about your business to get started.</p>

            {error && <div className="onboard-error">{error}</div>}

            <form className="onboard-form" onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Business Name</label>
                  <input value={merchantData.name} onChange={m("name")} placeholder="Your business name" required />
                </div>
                 <div className="form-group">
                  <label>Business Type</label>
                  <input value={merchantData.business_type} onChange={m("business_type")} placeholder="e.g. Retail, Wholesale" required />
                </div>
              </div>

              <div className="">
               
                <div className="form-group">
                  <label>Contact Person</label>
                  <input value={merchantData.contact_person} onChange={m("contact_person")} placeholder="Full name" required />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Phone Number</label>
                  <input value={merchantData.phone_number} onChange={m("phone_number")} placeholder="+254 7XX XXX XXX" required />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" value={merchantData.email} onChange={m("email")} required />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Avg Daily Sales</label>
                  <input type="number" min="0" value={merchantData.avg_daily_sales} onChange={m("avg_daily_sales")} placeholder="e.g. 50000" required />
                </div>
                <div className="form-group">
                  <label>Consistency (0–1)</label>
                  <input type="number" min="0" max="1" step="0.01" value={merchantData.consistency} onChange={m("consistency")} placeholder="e.g. 0.85" required />
                </div>
              </div>

              <div className="form-group">
                <label>Days Active</label>
                <input type="number" min="0" value={merchantData.days_active} onChange={m("days_active")} placeholder="e.g. 120" required />
              </div>

              <div className="onboard-actions">
                <button type="button" className="onboard-btn secondary" onClick={goBack} disabled={loading}>
                  ← Back
                </button>
                <button type="submit" className="onboard-btn primary" disabled={loading}>
                  {loading ? "Submitting…" : "Complete onboarding"}
                </button>
              </div>
            </form>
          </>
        )}

        {step === 2 && role === "supplier" && (
          <>
            <h2>Supplier details</h2>
            <p className="onboard-sub">Tell us about your supply business to get started.</p>

            {error && <div className="onboard-error">{error}</div>}

            <form className="onboard-form" onSubmit={handleSubmit}>
              <div className="">
                <div className="form-group">
                  <label>Business Name</label>
                  <input value={supplierData.name} onChange={s("name")} placeholder="Your business name" required />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Contact Person</label>
                  <input value={supplierData.contact_person} onChange={s("contact_person")} placeholder="Full name" required />
                </div>
                <div className="form-group">
                  <label>Phone Number</label>
                  <input value={supplierData.phone_number} onChange={s("phone_number")} placeholder="+254 7XX XXX XXX" required />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Email</label>
                  <input type="email" value={supplierData.email} onChange={s("email")} required />
                </div>
                <div className="form-group">
                  <label>Product Category</label>
                  <input value={supplierData.product_category} onChange={s("product_category")} placeholder="e.g. Electronics, FMCG" required />
                </div>
              </div>

              <div className="onboard-actions">
                <button type="button" className="onboard-btn secondary" onClick={goBack} disabled={loading}>
                  ← Back
                </button>
                <button type="submit" className="onboard-btn primary" disabled={loading}>
                  {loading ? "Submitting…" : "Complete onboarding"}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000",
  withCredentials: true,
});

// --- AUTH ---
export const loginUser = (email, password) => {
  const params = new URLSearchParams();
  params.append("username", email);
  params.append("password", password);
  return api.post("/auth/login", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" }
  });
};
export const registerUser   = (data) => api.post("/auth/register", data);
export const getCurrentUser = ()     => api.get("/auth/me");

// --- ONBOARDING ---
export const onboardMerchant = (data) => api.post("/merchants/onboard", data);
export const onboardSupplier = (data) => api.post("/suppliers/onboard", data);

// --- MERCHANT ---
export const getMerchantDashboard = ()     => api.get("/merchant/me/dashboard");
export const applyCredit          = (data) => api.post("/credit/apply", data);
export const recordRepayment      = (data) => api.post("/repayment/settle", data);

// --- SUPPLIER ---
export const getSupplierDashboard = ()  => api.get("/supplier/me/dashboard");
export const getAllSuppliers       = ()  => api.get("/suppliers");
export const approveContract      = (id) => api.post(`/supplier/contracts/${id}/approve`);
export const dispatchContract     = (id) => api.post(`/supplier/contracts/${id}/dispatch`);
export const confirmDelivery      = (id) => api.post(`/supplier/contracts/${id}/deliver`);

// --- ADMIN ---
export const getAdminOverview = () => api.get("/admin/overview");

export default api;

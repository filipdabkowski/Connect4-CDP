// import { useState } from 'react'
// import { Link, useNavigate } from "react-router-dom";
// import { useAuth } from "../auth/AuthContext";
//
// export default function Login() {
//   const nav = useNavigate();
//   const { login } = useAuth();
//
//   const [email, setEmail] = useState("");
//   const [password, setPassword] = useState("");
//   const [err, setErr] = useState("");
//   const [loading, setLoading] = useState(false);
//
//   async function onSubmit(e) {
//     e.preventDefault();
//     setErr("");
//
//     if (!email || !password) return setErr("Email and password are required.");
//
//     setLoading(true);
//     try {
//       await login(email, password);
//       nav("/dashboard");
//     } catch (e) {
//       // Third-party APIs often return e.response.data.message
//       const msg =
//         e?.response?.data?.message ||
//         e?.response?.data?.detail ||
//         "Login failed.";
//       setErr(msg);
//     } finally {
//       setLoading(false);
//     }
//   }
//
//   return (
//     <div style={{ maxWidth: 420, margin: "60px auto", fontFamily: "system-ui" }}>
//       <h1>Login</h1>
//       <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
//         <label>
//           Email
//           <input
//             value={email}
//             onChange={(e) => setEmail(e.target.value)}
//             type="email"
//             placeholder="you@example.com"
//             style={{ width: "100%", padding: 10, marginTop: 6 }}
//           />
//         </label>
//
//         <label>
//           Password
//           <input
//             value={password}
//             onChange={(e) => setPassword(e.target.value)}
//             type="password"
//             placeholder="••••••••"
//             style={{ width: "100%", padding: 10, marginTop: 6 }}
//           />
//         </label>
//
//         {err && <div style={{ color: "crimson" }}>{err}</div>}
//
//         <button disabled={loading} style={{ padding: 10 }}>
//           {loading ? "Signing in..." : "Sign in"}
//         </button>
//       </form>
//
//       <p style={{ marginTop: 16 }}>
//         No account? <Link to="/register">Register</Link>
//       </p>
//     </div>
//   );
// }

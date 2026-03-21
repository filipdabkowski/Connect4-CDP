import {Routes, Route} from "react-router-dom";
import './App.css'
import LoginPage from "./pages/Login.tsx";
import RegisterPage from "./pages/Register.tsx";
import HomePage from "./pages/Home.tsx"
import {ProtectedRoute} from "./routes/ProtectedRoute.tsx";
import {PublicRoute} from "./routes/PublicRoute.tsx";

function App() {

    return (
        <>
            <Routes>
                <Route path="/login" element={
                    <PublicRoute><LoginPage/></PublicRoute>
                }/>
                <Route path="/register" element={
                    <PublicRoute><RegisterPage/></PublicRoute>
                }/>
                
                <Route path="/" element={
                    <ProtectedRoute><HomePage/></ProtectedRoute>
                }/>
            </Routes>
        </>
    )
}

export default App

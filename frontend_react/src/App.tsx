import {Routes, Route} from "react-router-dom";
import './App.css'
import LoginPage from "./pages/Login.tsx";
import RegisterPage from "./pages/Register.tsx";

function App() {

    return (
        <>
            <Routes>
                <Route path="/" element={<LoginPage/>}/>
                <Route path="/register" element={<RegisterPage/>}/>

            </Routes>
        </>
    )
}

export default App

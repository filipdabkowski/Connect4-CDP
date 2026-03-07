import {Link} from "react-router-dom";
import React, {useState} from "react";
import MainButton from "../components/MainButton";
import FormInput from "../components/FormInput.tsx";

export default function LoginPage() {
    const [form, setForm] = useState({
        username: "",
        password: "",
        passwordConfirm: ""
    })

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
        const {name, value} = e.target;
        // Update form state, replace changed value
        setForm((prevState) => ({
            ...prevState,
            [name]: value
        }));
    }

    return (
        <div className="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-sm">
                <h2 className="text-center text-2xl/9 font-bold tracking-tight text-white">
                    Create new Player account
                </h2>
            </div>

            <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
                <form action="#" method="POST" className="space-y-5">
                    <FormInput
                        type="text"
                        name="username"
                        value={form.username}
                        placeholder="Pick Username"
                        required={true}
                        label="Username"
                        onChange={handleChange}
                    ></FormInput>

                    <FormInput
                        type="password"
                        name="password"
                        value={form.password}
                        placeholder="Input password"
                        required={true}
                        label="Password"
                        onChange={handleChange}
                    ></FormInput>
                    
                    <FormInput
                        type="password"
                        name="passwordConfirm"
                        value={form.passwordConfirm}
                        placeholder="Confirm password"
                        required={true}
                        label="Confirm"
                        onChange={handleChange}
                    ></FormInput>

                    <div>
                        <MainButton>Sign Up</MainButton>
                    </div>
                </form>

                <p className="mt-10 text-center text-sm/6 text-gray-400">
                    Already a Player? 
                    <Link to="/" className="font-semibold text-indigo-400 hover:text-indigo-300">
                        &nbsp;Login to your account
                    </Link>
                </p>
            </div>
        </div>
    )
}

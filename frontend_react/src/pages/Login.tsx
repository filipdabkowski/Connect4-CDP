import {Link} from "react-router-dom";
import React, {useState} from "react";
import MainButton from "../components/MainButton";
import FormInput from "../components/FormInput.tsx";
import {useAuth} from "../auth/useAuth.ts";
import {ApiValidationError} from "../api/auth.ts";


type LoginFieldErrors = {
    username?: string[];
    password?: string[];
    detail?: string;
};

export default function LoginPage() {
    const {login} = useAuth();

    const [form, setForm] = useState({
        username: "",
        password: ""
    })
    const [valid, setValid] = useState({
        username: true,
        password: true
    })
    const [errMessage, setErrMessage] = useState<LoginFieldErrors>()

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
        const {name, value} = e.target;
        // Update form state, replace changed value
        setForm((prevState) => ({
            ...prevState,
            [name]: value
        }));
        // After a change of invalid field assume it will be valid
        setValid((prevState) => ({
            ...prevState,
            [name]: true
        }));
    }

    async function submit(e: React.SubmitEvent) {
        e.preventDefault();
        // reset and assume it will be correct
        setValid({username: true, password: true});
        setErrMessage({});
        // check if both fields are filled
        if (!form.username || !form.password) {
            setValid({username: !!form.username, password: !!form.password})
            setErrMessage({
                username: valid.username ? undefined : ["Username required."],
                password: valid.password ? undefined : ["Password required."]
            })
            return
        }

        try {
            await login({username: form.username, password: form.password})
        } catch (err) {
            if (err instanceof ApiValidationError) {
                const errors = err.fieldErrors;
                console.log(errors)
                setErrMessage(errors);
                // fields that have an error, mark as invalid
                setValid((prevState) => ({
                    ...prevState,
                    ...Object.fromEntries(
                        Object.keys(errors).map((key) => [key, false])
                    ),
                }))
            }
        }
    }

    return (
        <div className="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-sm">
                <h2 className="text-center text-2xl/9 font-bold tracking-tight text-white">
                    Sign in to your account
                </h2>
            </div>

            <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
                <form action="#" method="POST" className="space-y-5" onSubmit={submit}>
                    <FormInput
                        type="text"
                        name="username"
                        value={form.username}
                        placeholder="Input Username"
                        required={true}
                        label="Username"
                        onChange={handleChange}
                        valid={valid.username}
                        validMessage={errMessage?.username}
                    ></FormInput>

                    <FormInput
                        type="password"
                        name="password"
                        value={form.password}
                        placeholder="Hope you didn't forget"
                        required={true}
                        label="Password"
                        onChange={handleChange}
                        valid={valid.password}
                        validMessage={errMessage?.password}
                    ></FormInput>

                    {errMessage?.detail && <p className="text-sm mt-2 text-pink-600">{errMessage?.detail}</p>}

                    <div>
                        <MainButton>Sign In</MainButton>
                    </div>
                </form>

                <p className="mt-10 text-center text-sm/6 text-gray-400">
                    Not a player yet?
                    <Link to="/register" className="font-semibold text-indigo-400 hover:text-indigo-300">
                        &nbsp;Create an account now
                    </Link>
                </p>
            </div>
        </div>
    )
}

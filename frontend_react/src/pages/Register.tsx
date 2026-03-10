import {Link, useNavigate} from "react-router-dom";
import React, {useEffect, useState} from "react";
import MainButton from "../components/MainButton";
import FormInput from "../components/FormInput.tsx";
import {useAuth} from "../auth/useAuth.ts";
import {ApiValidationError} from "../api/auth.ts";


type RegisterFieldErrors = {
    username?: string[];
    password?: string[];
    passwordConfirm?: string[];
};

export default function RegisterPage() {
    const {register, isAuth} = useAuth();
    const navigate = useNavigate();

    const [form, setForm] = useState({
        username: "",
        password: "",
        passwordConfirm: ""
    })
    const [valid, setValid] = useState({
        username: true,
        password: true,
        passwordConfirm: true
    })
    const [errMessage, setErrMessage] = useState<RegisterFieldErrors>()

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

    async function handleSubmit(e: React.SubmitEvent) {
        e.preventDefault();
        // reset and assume it will be correct
        setValid({username: true, password: true, passwordConfirm: true});
        setErrMessage({});
        // check if all fields are filled
        if (!form.username || !form.password || !form.passwordConfirm) {
            setValid({username: !!form.username, password: !!form.password, passwordConfirm: !!form.passwordConfirm});
            setErrMessage({
                username: valid.username ? undefined : ["Username required."],
                password: valid.password ? undefined : ["Password required."],
                passwordConfirm: valid.passwordConfirm ? undefined : ["Confirm password."]
            });
            return
        }
        // check if passwords match
        if (form.password != form.passwordConfirm) {
            setValid({
                ...valid,
                password: false,
                passwordConfirm: false,
            })
            setErrMessage({
                ...errMessage,
                password: ["Passwords do not match."],
                passwordConfirm: ["Passwords do not match."]
            })
            return
        }

        try {
            await register({username: form.username, password: form.password});
            navigate("/");
        } catch (err) {
            if (err instanceof ApiValidationError) {
                const errors = err.fieldErrors;
                console.log(errors);
                setErrMessage(errors);
                setValid((prevState) => ({
                    ...prevState,
                    ...Object.fromEntries(
                        Object.keys(errors).map((key) => [key, false])
                    ),
                }))
            }
        }
    }

    // on load
    useEffect(() => {
        if (isAuth) {
            navigate("/");
        }
    }, [isAuth, navigate]);

    return (
        <div className="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8">
            <div className="sm:mx-auto sm:w-full sm:max-w-sm">
                <h2 className="text-center text-2xl/9 font-bold tracking-tight text-white">
                    Create new Player account
                </h2>
            </div>

            <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
                <form action="#" method="POST" className="space-y-5" onSubmit={handleSubmit}>
                    <FormInput
                        type="text"
                        name="username"
                        value={form.username}
                        placeholder="Pick Username"
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
                        placeholder="Input password"
                        required={true}
                        label="Password"
                        onChange={handleChange}
                        valid={valid.password}
                        validMessage={errMessage?.password}
                    ></FormInput>

                    <FormInput
                        type="password"
                        name="passwordConfirm"
                        value={form.passwordConfirm}
                        placeholder="Confirm password"
                        required={true}
                        label="Confirm"
                        onChange={handleChange}
                        valid={valid.passwordConfirm}
                        validMessage={errMessage?.passwordConfirm}
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

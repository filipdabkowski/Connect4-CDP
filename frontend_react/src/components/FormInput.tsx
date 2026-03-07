import React, {useId} from "react";

type FormInputProps = {
    type: string;
    name: string,
    label?: string;
    value: string;
    required?: boolean;
    placeholder?: string;
    onChange?: (value: React.ChangeEvent<HTMLInputElement>) => void;
    valid?: boolean;
    validMessage?: string;
};

export default function FormInput({type, name, label, value, required, placeholder, onChange, valid, validMessage}: FormInputProps) {
    const id = useId();

    return (
        <div>
            {label && (
                <label htmlFor={id} className="block text-sm/6 font-medium text-gray-100">{label}</label>
            )}
            <div className="mt-2">
                <input
                    id={id}
                    name={name}
                    type={type}
                    placeholder={placeholder}
                    required={required}
                    value={value}
                    onChange={(e) => onChange ? onChange(e) : void 0}
                    aria-invalid={!valid}
                    className={`
                        block w-full rounded-md bg-white/5 px-3 py-1.5 text-base outline-1 -outline-offset-1 focus:outline-2 focus:-outline-offset-2 placeholder:text-gray-500 sm:text-sm/6
                        ${!valid ? "text-pink-600 outline-pink-500 focus:outline-pink-500" : "text-white outline-white/10 focus:outline-indigo-500"}
                    `}
                />
                {(validMessage) && <p className="text-sm mt-2 text-pink-600">Hello worlsd</p>}
            </div>
        </div>
    );
}

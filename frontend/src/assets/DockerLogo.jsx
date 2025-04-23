import React from "react";
import { Box } from "@mui/material";

export default function DockerLogo({ size = 48, mr = 0 }) {
  return (
    <Box style={{ marginRight: mr }} display="flex" alignItems="center" justifyContent={"center"}>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        aria-label="Docker"
        role="img"
        viewBox="0 0 512 512"
        width={size}
        height={size}
        fill="#000000"
      >
        <g id="SVGRepo_bgCarrier" strokeWidth="0"></g>
        <g
          id="SVGRepo_tracerCarrier"
          strokeLinecap="round"
          strokeLinejoin="round"
        ></g>
        <g id="SVGRepo_iconCarrier">
          <path
            stroke="#42bdff"
            strokeWidth="38"
            d="M296 226h42m-92 0h42m-91 0h42m-91 0h41m-91 0h42m8-46h41m8 0h42m7 0h42m-42-46h42"
          ></path>
          <path
            fill="#42bdff"
            d="m472 228s-18-17-55-11c-4-29-35-46-35-46s-29 35-8 74c-6 3-16 7-31 7H68c-5 19-5 145 133 145 99 0 173-46 208-130 52 4 63-39 63-39"
          ></path>
        </g>
      </svg>
    </Box>
  );
}

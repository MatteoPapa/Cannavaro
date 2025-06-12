import React from "react";
import { Box } from "@mui/material";

export default function GitLogo({ size = 48, mr = 0 }) {
  return (
    <Box
      style={{ marginRight: mr }}
      display="flex"
      alignItems="center"
      justifyContent="center"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 97.75 97.75"
        width={size}
        height={size}
        fill="none"
      >
        <path
          fill="#F1502F"
          d="M92.71 44.408 53.34 5.036a6.29 6.29 0 0 0-8.889 0l-7.299 7.298 9.075 9.074a7.251 7.251 0 0 1 9.25 9.247l8.734 8.733a7.25 7.25 0 1 1-4.597 4.596l-7.876-7.876v20.479a7.25 7.25 0 1 1-5.253-.095V35.539a7.26 7.26 0 0 1-3.234-9.572l-9.001-9.001L5.04 44.408a6.29 6.29 0 0 0 0 8.888l39.372 39.371a6.29 6.29 0 0 0 8.889 0l39.409-39.371a6.29 6.29 0 0 0 0-8.888z"
        />
      </svg>
    </Box>
  );
}


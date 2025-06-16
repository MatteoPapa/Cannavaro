import React, { useState } from "react";
import {
  Popper,
  IconButton,
  ClickAwayListener,
  Typography,
  Box,
} from "@mui/material";
import InfoOutlineIcon from "@mui/icons-material/InfoOutlined";
import DetailsMenu from "../components/DetailsMenu";

const InfoWithDetails = ({ service }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);

  const handleMouseEnter = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMouseLeave = () => {
    setAnchorEl(null);
  };

  return (
    <div
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{ display: "inline-block" }}
    >
      <IconButton>
        <InfoOutlineIcon fontSize="small" color="action" />
      </IconButton>
      <Popper
        open={open}
        anchorEl={anchorEl}
        placement="bottom-start"
        modifiers={[
          {
            name: "offset",
            options: {
              offset: [0, 8], // X, Y offset
            },
          },
        ]}
        style={{ zIndex: 1300 }}
      >
        <Box
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          sx={{
            boxShadow: 6,
            borderRadius: 4,
            p: 2,
            maxWidth: 300,
            bgcolor: "background.paper",
          }}
        >
          <DetailsMenu name="Environment" list={service.environment} />
          <DetailsMenu name="Mounted Volumes" list={service.volumes} />
          <DetailsMenu name="Exposed Ports" list={service.ports} />
        </Box>
      </Popper>
    </div>
  );
};

export default InfoWithDetails;

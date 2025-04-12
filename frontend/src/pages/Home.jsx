import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Container,
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
} from "@mui/material";
import { Memory } from "@mui/icons-material";
import ComputerIcon from "@mui/icons-material/Computer";

function Home() {
  const [services, setServices] = useState([]);
  const [vmIp, setVmIp] = useState("");

  useEffect(() => {
    fetch("/api/services")
      .then((res) => res.json())
      .then(setServices);

    fetch("/api/vm_ip")
      .then((res) => res.json())
      .then((data) => {
        console.log(data);
        setVmIp(data);
      });
  }, []);

  return (
    <>
      <Box>
        <Box display={"flex"} justifyContent="center" mt={5}>
          <img
            src="cannavaro.png"
            alt=""
            width={100}
            height={100}
            style={{
              transform: "translateX(55px)",
              zIndex: -1,
            }}
          />
          <Typography
            variant="h2"
            color="primary"
            sx={{
              fontWeight: "bold",
              textAlign: "center",
              mt: 5,
              textShadow: "2px 2px 7px rgb(0, 46, 59)",
            }}
            gutterBottom
          >
            CANNAVARO
          </Typography>
        </Box>
      </Box>

      <Container
        maxWidth="md"
        sx={{
          mt: 5,
          p: 3,
          border: 1,
          borderColor: "primary.main",
          borderRadius: 2,
        }}
      >
        <Box
          display={"flex"}
          alignItems="center"
          justifyContent="center"
          gap={1}
          mb={2}
        >
          <Typography variant="h4" color="primary" gutterBottom>
            <ComputerIcon fontSize="medium" color="primary" sx={{ mr: 1 }} />
            VulnBox:
          </Typography>
          <Typography variant="h4" gutterBottom>
            {vmIp}
          </Typography>
        </Box>

        {/* Flex container using dflex */}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 2,
          }}
        >
          {services.map((service) => (
            <Card
              key={service.name}
              variant="outlined"
              component={Link}
              to={`/service/${service.name}`}
              sx={{
                textDecoration: "none",
                bgcolor: "background.paper",
                color: "text.primary",
                transition: "0.3s",
                borderRadius: 2,
                p: 2,
                "&:hover": {
                  boxShadow: 6,
                  transform: "translateY(-2px)",
                },
              }}
            >
              <CardContent>
                <Box
                  display="flex"
                  alignItems="center"
                  justifyContent="center"
                  gap={1}
                  mb={2}
                >
                  <Memory fontSize="small" color="primary" />
                  <Typography variant="h6" textAlign="center">
                    {service.name}
                  </Typography>
                </Box>
                <Chip
                  label={`Port ${service.port}`}
                  color="primary"
                  variant="outlined"
                />
              </CardContent>
            </Card>
          ))}
        </Box>
      </Container>
    </>
  );
}

export default Home;

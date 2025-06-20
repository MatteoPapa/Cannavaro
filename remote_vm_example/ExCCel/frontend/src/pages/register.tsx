import React, { FunctionComponent, useState } from 'react'
import { Button, Col, Container, Form, InputGroup, Row } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import API from '../api'
import { useAsyncCallback } from '../utils'

const Register: FunctionComponent = () => {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const register = useAsyncCallback(async () => {
    await API.register(username, password)
    navigate('/')
  }, [username, password, navigate])

  return <Container>
    <Row className="justify-content-center">
      <Col lg={4} className="text-center mt-5">
        <h1 className="text-white mb-3">Register</h1>
        <InputGroup className="mb-3">
          <InputGroup.Text>Username</InputGroup.Text>
          <Form.Control
            type="text"
            placeholder="Username"
            value={username}
            onChange={(ev) => setUsername(ev.target.value)}
          />
        </InputGroup>
        <InputGroup className="mb-3">
          <InputGroup.Text>Password&nbsp;</InputGroup.Text>
          <Form.Control
            type="password"
            placeholder="Password"
            value={password}
            onChange={(ev) => setPassword(ev.target.value)}
          />
        </InputGroup>

        <Button onClick={register}>Register</Button>
      </Col>
    </Row>
  </Container>
}

export default Register
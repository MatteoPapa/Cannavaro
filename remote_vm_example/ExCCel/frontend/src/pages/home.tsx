import React, { FunctionComponent, useEffect, useState } from 'react'
import { Button, Col, Container, Image, Row } from 'react-bootstrap'
import logoPng from '../../assets/logo.png'
import API, { User } from '../api'
import { useAsyncCallback } from '../utils'


const Home: FunctionComponent = () => {
  const [user, setUser] = useState<User | null>(null)

  const loadUser = useAsyncCallback(async () => {
    const user = await API.user()
    if (!user.logged) {
      setUser(null)
      return
    }

    setUser(user)
  }, [])

  const logout = useAsyncCallback(async () => {
    await API.logout()
    loadUser()
  }, [loadUser])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  return <Container>
    <Row className="justify-content-center">
      <Col lg={4} className="text-center mt-5">
        <Image src={logoPng} height={200}/>
        <h1 className="text-white mt-2">ExCCel</h1>
      </Col>
    </Row>
    <Row className="justify-content-center">
      <Col lg={4} className="text-center mt-5">
        {user ? <>
          <Button className="me-2" onClick={logout}>Logout</Button>
          <Button href="/worksheets">My worksheets</Button>
        </> : <>
          <Button className="me-2" href="/login">Login</Button>
          <Button href="/register">Register</Button>
        </>}
      </Col>
    </Row>
  </Container>
}

export default Home
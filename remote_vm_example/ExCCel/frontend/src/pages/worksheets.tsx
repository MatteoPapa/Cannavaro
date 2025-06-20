import React, { FunctionComponent, useEffect, useState } from 'react'
import { Button, Col, Container, Form, InputGroup, ListGroup, ListGroupItem, Row } from 'react-bootstrap'
import API, { User, WorksheetLight } from '../api'
import { useAsyncCallback } from '../utils'
import { Link, useNavigate } from 'react-router-dom'

const Worksheets: FunctionComponent = () => {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [worksheets, setWorksheets] = useState<Array<WorksheetLight>>([])

  const loadWorksheets = useAsyncCallback(async () => {
    const worksheets = await API.getWorksheets()
    setWorksheets(worksheets)
  }, [])

  const loadUser = useAsyncCallback(async () => {
    const user = await API.user()
    if (!user.logged) {
      setUser(null)
      return
    }

    setUser(user)
  }, [])

  const [createWorksheetTitle, setCreateWorksheetTitle] = useState('')
  const [createWorksheetSharable, setCreateWorksheetSharable] = useState(false)

  const createWorksheet = useAsyncCallback(async () => {
    if (!createWorksheetTitle) {
      return
    }

    const worksheet = await API.createWorksheet(createWorksheetTitle, createWorksheetSharable)
    navigate(`/worksheet/${worksheet.id}`)
  }, [navigate, createWorksheetTitle, createWorksheetSharable])

  useEffect(() => {
    loadUser()
    loadWorksheets()
  }, [loadWorksheets])

  if (!user) {
    return <></>
  }

  return <Container>
    <Row className="justify-content-center">
      <Col lg={6} className="text-center mt-5">
        <h1 className="text-white mb-3">Worksheets</h1>

        <InputGroup className="mb-3">
          <Form.Control
            type="text"
            placeholder="Title"
            value={createWorksheetTitle}
            onChange={(ev) => setCreateWorksheetTitle(ev.target.value)}
          />
          <InputGroup.Text>
            <Form.Check
              checked={createWorksheetSharable}
              onChange={(ev) => setCreateWorksheetSharable(ev.target.checked)}
              label="Sharable"
            />
          </InputGroup.Text>
          <Button onClick={createWorksheet}>Create new</Button>
        </InputGroup>

        <ListGroup>
          {worksheets.map(w => (
            <ListGroupItem key={w.id}><Link to={`/worksheet/${w.id}`}>{w.title}</Link> ({user.id === w.owner.id
              ? (w.sharable
                ? 'Sharable'
                : 'Not sharable')
              : `Shared by ${w.owner.username}`})</ListGroupItem>))}
        </ListGroup>
      </Col>
    </Row>
  </Container>
}

export default Worksheets
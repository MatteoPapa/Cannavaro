import React, { FunctionComponent, useEffect, useState } from 'react'
import API, { User, Worksheet, WorksheetCell } from '../api'
import { cellXYToCoords, hexDecode, hexEncode, useAsyncCallback } from '../utils'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import Spreadsheet, { CellBase, DataEditorProps, DataViewerProps, Matrix } from 'react-spreadsheet'
import { Button, Card, Form } from 'react-bootstrap'
import classNames from 'classnames'

type Cell = CellBase<{ content: string, evaluated?: string }>

const CustomDataViewer: FunctionComponent<DataViewerProps<Cell>> = (props) => {
  return (
    <span
      className={classNames('Spreadsheet__data-viewer', {
        'Spreadsheet__data-viewer--preserve-breaks': false,
      })}
    >
      {props.cell?.value?.evaluated || props.cell?.value?.content}
    </span>
  )
}

const CustomDataEditor: FunctionComponent<DataEditorProps<Cell>> = (props) => {
  const handleChange = React.useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      props.onChange({...props.cell, value: {content: event.target.value}})
    },
    [props]
  )

  return (
    <div className="Spreadsheet__data-editor">
      <input
        type="text"
        onChange={handleChange}
        value={props.cell?.value?.content || ''}
        autoFocus
      />
    </div>
  )
}

const Worksheet: FunctionComponent = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const {id} = useParams<{ id: string }>()
  const [user, setUser] = useState<User | null>(null)
  const [worksheet, setWorksheet] = useState<Worksheet | null>(null)
  const [shareToken, setShareToken] = useState('')
  const [data, setData] = useState<Matrix<Cell>>([])
  const [selectedCell, setSelectedCell] = useState<[number, number] | null>(null)
  const [newCommentContent, setNewCommentContent] = useState('')

  useEffect(() => {
    if (!worksheet) {
      return
    }

    const data: Matrix<Cell> = []
    for (let y = 0; y < 64; y++) {
      const row: Array<Cell> = []
      for (let x = 0; x < 64; x++) {
        row.push({
          value: {content: ''},
        })
      }
      data.push(row)
    }

    for (const cell of worksheet.cells) {
      data[cell.y][cell.x].value = {content: hexDecode(cell.content), evaluated: hexDecode(cell.evaluated)}
    }

    setData(data)
  }, [worksheet])

  const loadWorksheet = useAsyncCallback(async () => {
    const worksheet = await API.getWorksheet(id)
    setWorksheet(worksheet)
  }, [id])

  const saveWorksheet = useAsyncCallback(async () => {
    const cells: WorksheetCell[] = []
    for (let y = 0; y < 64; y++) {
      for (let x = 0; x < 64; x++) {
        const cell = data[y][x].value
        if (!cell || !cell.content) {
          continue
        }

        cells.push({x, y, content: hexEncode(cell.content)})
      }
    }

    const worksheet = await API.saveWorksheet(id, cells)
    setWorksheet(worksheet)
  }, [id, data])

  const createComment = useAsyncCallback(async () => {
    if (!newCommentContent || !selectedCell) {
      return
    }

    await API.createComment(id, selectedCell[0], selectedCell[1], newCommentContent)
    setNewCommentContent('')

    loadWorksheet()
  }, [id, newCommentContent, selectedCell, loadWorksheet])

  const shareWorksheet = useAsyncCallback(async () => {
    if (!worksheet) {
      return
    }

    const share = await API.shareWorksheet(worksheet.id)
    setShareToken(share.token)
  }, [worksheet])

  const loadUser = useAsyncCallback(async () => {
    const user = await API.user()
    if (!user.logged) {
      setUser(null)
      return
    }

    setUser(user)
  }, [])

  const acceptWorksheetInvite = useAsyncCallback(async (invite: string) => {
    await API.acceptWorksheetInvite(id, invite)
    navigate(`/worksheet/${id}`, {replace: true})
  }, [id, navigate])

  useEffect(() => {
    loadUser()

    const query = new URLSearchParams(location.search)
    const invite = query.get('invite')
    if (invite) {
      acceptWorksheetInvite(invite)
    } else {
      loadWorksheet()
    }
  }, [loadUser, loadWorksheet, acceptWorksheetInvite, location.search])

  if (!worksheet || !user) {
    return <></>
  }

  return <div className="h-100 d-flex flex-column p-3">
    <div className="d-flex flex-row mb-3">
      <div className="flex-grow-1">
        <h1 className="text-white">{worksheet.title}</h1>
        <h4 className="text-muted">{
          user.id === worksheet.owner.id
            ? (worksheet.sharable
              ? `Sharable, ${worksheet.guests.length} guests`
              : 'Not sharable')
            : `Shared by ${worksheet.owner.username}`
        }</h4>
      </div>
      {user.id === worksheet.owner.id && worksheet.sharable &&
        <div>
          <Button onClick={shareWorksheet} className="float-end ms-3">Share</Button>
          {shareToken && <code>{`${window.location.origin}/worksheet/${worksheet.id}?invite=${shareToken}`}</code>}
        </div>
      }
    </div>
    <div className="flex-1 d-grid gap-4" style={{gridTemplateColumns: '5fr 1fr', minHeight: 0}}>
      <div className="overflow-auto">
        <Spreadsheet
          data={data}
          onChange={(newData) => setData((prevData) => {
            for (let y = 0; y < 64; y++) {
              for (let x = 0; x < 64; x++) {
                if (prevData[y][x].value?.content !== newData[y][x].value?.content) {
                  return newData
                }
              }
            }

            return prevData
          })}
          onActivate={(p) => setSelectedCell([p.column, p.row])}
          DataViewer={CustomDataViewer}
          DataEditor={CustomDataEditor}
          onModeChange={(mode) => {
            if (mode === 'edit') {
              return
            }

            saveWorksheet()
          }}
        />
      </div>
      <div className="d-flex flex-column">
        <h4 className="text-white">Comments</h4>
        <div className="flex-grow-1 mb-2 mt-2">
          {worksheet.comments?.map(c => (<Card
            key={c.id}
            className={classNames('mb-2', {
              'text-white': selectedCell && c.x === selectedCell[0] && c.y === selectedCell[1]
            })}
            bg={selectedCell && c.x === selectedCell[0] && c.y === selectedCell[1] ? 'primary' : undefined}
          >
            <Card.Body>
              <Card.Text>{c.content}</Card.Text>
            </Card.Body>
            <Card.Footer>
              {cellXYToCoords(c.x, c.y)} - @{c.owner.username}
            </Card.Footer>
          </Card>))}
        </div>
        <small>Selected cell: {selectedCell && cellXYToCoords(selectedCell[0], selectedCell[1])}</small>
        <Form.Control
          as="textarea"
          className="mb-2"
          value={newCommentContent}
          onChange={(ev) => setNewCommentContent(ev.target.value)}
        />
        <Button onClick={createComment} disabled={!newCommentContent || !selectedCell}>Add comment</Button>
      </div>
    </div>
  </div>
}

export default Worksheet
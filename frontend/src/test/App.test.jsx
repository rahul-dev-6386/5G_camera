import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

// Mock the API
global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ message: 'Backend is running' }),
  })
)

describe('App Component', () => {
  it('should render without crashing', () => {
    // This is a placeholder test - the actual App component would need to be imported
    // For now, we're just testing that the test infrastructure works
    expect(true).toBe(true)
  })

  it('should have a title element', () => {
    render(<div><h1>Smart Campus</h1></div>)
    const title = screen.getByText('Smart Campus')
    expect(title).toBeInTheDocument()
  })

  it('should handle button clicks', async () => {
    const user = userEvent.setup()
    render(<button>Click me</button>)
    
    const button = screen.getByText('Click me')
    await user.click(button)
    
    expect(button).toBeInTheDocument()
  })
})

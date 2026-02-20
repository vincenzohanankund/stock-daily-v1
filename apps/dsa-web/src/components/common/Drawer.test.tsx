import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import Drawer from './Drawer';

describe('Drawer', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    title: 'Test Drawer',
    children: <div>Drawer Content</div>,
  };

  it('renders correctly', () => {
    render(<Drawer {...defaultProps} />);
    expect(screen.getByText('Test Drawer')).toBeInTheDocument();
    expect(screen.getByText('Drawer Content')).toBeInTheDocument();
  });

  it('applies correct position classes', () => {
    const { container } = render(<Drawer {...defaultProps} position="left" />);
    // The drawer panel is the second child (first is backdrop)
    const drawerPanel = container.querySelector('.fixed.inset-y-0');
    expect(drawerPanel).toHaveClass('left-0');
    expect(drawerPanel).not.toHaveClass('right-0');
  });

  it('calls onClose when close button is clicked', () => {
    render(<Drawer {...defaultProps} />);
    // Drawer uses X icon inside a button
    // The button might not have an accessible name "close", but it has the X icon.
    // Let's look at the implementation: 
    // <button onClick={handleClose} ...><X size={20} /></button>
    // It doesn't have aria-label or text.
    // Wait, the implementation of Drawer I read earlier:
    // <button onClick={handleClose} ...><X size={20} /></button>
    // It is a button.
    
    // Let's try to find by role button. There might be multiple if children has buttons.
    // But here children is simple div.
    const buttons = screen.getAllByRole('button');
    // The close button is likely the first one or we can find by class or verify logic.
    // Better to add aria-label to Drawer close button in source code for accessibility!
    // But for now, let's assume it's the only button or find by selector.
    fireEvent.click(buttons[0]);
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('calls onClose when Escape key is pressed', () => {
    render(<Drawer {...defaultProps} />);
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { expectAccessible } from '../test/accessibility'
import { Alert, Button, Chip, KindBadge, PageHead, Progress, Rail, ReasonLabel,
  SectionRow, StatusRegion, Stepper, SummaryText, Switch } from './ui'
import { useJump } from './useJump'

describe('shared components', () => {
  it('limits the switch label to the track and text and links its description', async () => {
    const { container } = render(<><Switch label="Fetch captions locally" checked={false}
      onChange={() => {}} describedBy="risk"/><p id="risk">Caption fetching may be blocked.</p></>)
    const input = screen.getByRole('switch', { name: 'Fetch captions locally' })
    expect(input).toHaveAttribute('aria-describedby', 'risk')
    expect(input.closest('label')?.querySelectorAll('span')).toHaveLength(2)
    await expectAccessible(container)
  })

  it('names each step and its progress', async () => {
    const { container } = render(<><Stepper current="summarizing"/>
      <Progress label="Items summarized: 5 of 12" value={5} max={12}/></>)
    expect(screen.getByText(/Checking sources/)).toHaveTextContent('(done)')
    expect(screen.getByText(/Summarizing/)).toHaveTextContent('(in progress)')
    expect(screen.getByText(/Grouping topics/)).toHaveTextContent('(next)')
    expect(screen.getByRole('progressbar', { name: 'Items summarized: 5 of 12' })).toHaveAttribute('value', '5')
    await expectAccessible(container)
  })

  it('preserves paragraph/list order and marks language', async () => {
    const { container } = render(<SummaryText lang="zh-Hans" text={'Paragraph\n- First\n- Second\nAfter'}/>)
    expect([...container.querySelector('.summary')!.children].map(node => node.tagName)).toEqual(['P', 'UL', 'P'])
    expect(container.querySelector('.summary')).toHaveAttribute('lang', 'zh-Hans')
    await expectAccessible(container)
  })

  it('uses readable reasons and source kind names', async () => {
    const { container } = render(<><KindBadge kind="youtube"/>
      {(['captions_off', 'no_captions', 'blocked', 'captions_failed', 'no_transcript'] as const)
        .map(reason => <ReasonLabel key={reason} reason={reason}/>)}</>)
    expect(screen.getByText('YouTube channel')).toBeInTheDocument()
    for (const text of ['Caption fetching is off', 'This video has no captions', 'Blocked by YouTube',
      'Captions could not be fetched', 'No transcript within 7 days']) {
      expect(screen.getByText(text)).toBeInTheDocument()
    }
    await expectAccessible(container)
  })

  it('moves focus without motion when the preference requests it', async () => {
    const scroll = vi.fn()
    vi.stubGlobal('matchMedia', () => ({ matches: true }))
    function Jump() {
      const jump = useJump('destination')
      return <><a href="#destination" onClick={jump}>Jump</a>
        <div id="destination" tabIndex={-1} ref={node => { if (node) node.scrollIntoView = scroll }}>
          Destination
        </div></>
    }
    try {
      const { container } = render(<Jump/>)
      fireEvent.click(screen.getByRole('link', { name: 'Jump' }))
      expect(document.activeElement).toBe(screen.getByText('Destination'))
      expect(scroll).toHaveBeenCalledWith({ behavior: 'auto' })
      await expectAccessible(container)
    } finally {
      vi.unstubAllGlobals()
    }
  })

  it('exposes accessible layouts, controls and status', async () => {
    const { container } = render(<>
      <PageHead title="Sources" lede="Your subscriptions"/>
      <SectionRow title="Topic" overview="Overview"><div className="items">A story</div></SectionRow>
      <Rail><h2>About</h2><p>Context</p></Rail>
      <Button variant="primary">Save</Button><Chip tone="ok">New items</Chip>
      <Alert title="Notice">Something happened</Alert><StatusRegion>Ready</StatusRegion>
    </>)
    expect(screen.getByRole('status')).toHaveTextContent('Ready')
    expect(screen.queryByRole('alert')).toBeNull()
    await expectAccessible(container)
  })
  it('announces error alerts but not informational notices', async () => {
    const { container } = render(<><Alert title="Note">No action required.</Alert>
      <Alert tone="error" title="Failed">Try again.</Alert></>)
    expect(screen.getByRole('alert')).toHaveTextContent('Failed')
    expect(screen.getByRole('alert')).not.toHaveTextContent('No action required.')
    await expectAccessible(container)
  })
})

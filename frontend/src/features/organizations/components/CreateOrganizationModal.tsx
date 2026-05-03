import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Chip,
  CircularProgress,
} from '@mui/material';
import { useTargetsWithoutOrganization, useCreateOrganization, useUpdateOrganization } from '../api';
import type { Organization } from '../orgTypes';

interface CreateOrganizationModalProps {
  open: boolean;
  onClose: () => void;
  organization?: Organization; // If provided, we are in Edit mode
  projectSlug: string;
}

const ITEM_HEIGHT = 48;
const ITEM_PADDING_TOP = 8;
const MenuProps = {
  paperprops: {
    style: {
      maxHeight: ITEM_HEIGHT * 4.5 + ITEM_PADDING_TOP,
      width: 250,
      backgroundColor: '#0a0a0f',
      border: '1px solid #1a1a2e',
      color: '#fff',
    },
  },
};

export const CreateOrganizationModal: React.FC<CreateOrganizationModalProps> = ({
  open,
  onClose,
  organization,
  projectSlug,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedDomains, setSelectedDomains] = useState<number[]>([]);

  const { data: availableTargets, isLoading: isLoadingTargets } = useTargetsWithoutOrganization();
  const createMutation = useCreateOrganization();
  const updateMutation = useUpdateOrganization();

  useEffect(() => {
    if (organization) {
      setName(organization.name);
      setDescription(organization.description || '');
      setSelectedDomains(organization.domains || []);
    } else {
      setName('');
      setDescription('');
      setSelectedDomains([]);
    }
  }, [organization, open]);

  const handleSubmit = async () => {
    if (!name) return;

    try {
      if (organization) {
        await updateMutation.mutateAsync({
          id: organization.id,
          name,
          description,
          domains: selectedDomains,
        });
      } else {
        await createMutation.mutateAsync({
          name,
          description,
          domains: selectedDomains,
          project: projectSlug as any, // Project ID or Slug depending on API
          slug: projectSlug
        });
      }
      onClose();
    } catch (error) {
      console.error('Failed to save organization:', error);
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            backgroundColor: '#0a0a0f',
            backgroundImage: 'linear-gradient(to bottom right, rgba(0, 243, 255, 0.05), rgba(255, 0, 60, 0.05))',
            border: '1px solid #1a1a2e',
            color: '#fff',
            boxShadow: '0 0 20px rgba(0, 0, 0, 0.5)',
          }
        }
      }}
    >
      <DialogTitle sx={{ borderBottom: '1px solid #1a1a2e', py: 2 }}>
        <Typography variant="h6" sx={{ color: '#00f3ff', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px' }}>
          {organization ? 'Edit Organization' : 'Create New Organization'}
        </Typography>
      </DialogTitle>
      <DialogContent sx={{ py: 3 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
          <TextField
            label="Organization Name"
            fullWidth
            value={name}
            onChange={(e) => setName(e.target.value)}
            variant="outlined"
            required
            InputProps={{
              sx: { color: '#fff', '& .MuiOutlinedInput-notchedOutline': { borderColor: '#1a1a2e' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#00f3ff' } }
            }}
            slotProps={{
              inputLabel: { sx: { color: 'rgba(255, 255, 255, 0.7)' } }
            }}
          />
          <TextField
            label="Description (Optional)"
            fullWidth
            multiline
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            variant="outlined"
            InputProps={{
              sx: { color: '#fff', '& .MuiOutlinedInput-notchedOutline': { borderColor: '#1a1a2e' }, '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#00f3ff' } }
            }}
            slotProps={{
              inputLabel: { sx: { color: 'rgba(255, 255, 255, 0.7)' } }
            }}
          />

          <FormControl fullWidth>
            <InputLabel id="domains-label" sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>Select Targets</InputLabel>
            <Select
              labelId="domains-label"
              id="domains-select"
              multiple
              value={selectedDomains}
              onChange={(e) => setSelectedDomains(typeof e.target.value === 'string' ? e.target.value.split(',').map(Number) : e.target.value)}
              input={<OutlinedInput label="Select Targets" sx={{
                color: '#fff',
                '& .MuiOutlinedInput-notchedOutline': { borderColor: '#1a1a2e' },
                '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#00f3ff' }
              }} />}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => {
                    const target = availableTargets?.find(t => t.id === value);
                    return (
                      <Chip
                        key={value}
                        label={target?.name || value}
                        sx={{
                          backgroundColor: 'rgba(0, 243, 255, 0.1)',
                          color: '#00f3ff',
                          border: '1px solid rgba(0, 243, 255, 0.3)',
                          '& .MuiChip-deleteIcon': { color: '#00f3ff' }
                        }}
                      />
                    );
                  })}
                </Box>
              )}
              MenuProps={MenuProps}
            >
              {isLoadingTargets ? (
                <MenuItem disabled>
                  <CircularProgress size={24} sx={{ color: '#00f3ff' }} />
                </MenuItem>
              ) : availableTargets?.length === 0 ? (
                <MenuItem disabled>No available targets</MenuItem>
              ) : (
                availableTargets?.map((target) => (
                  <MenuItem key={target.id} value={target.id} sx={{
                    '&.Mui-selected': { backgroundColor: 'rgba(0, 243, 255, 0.2)' },
                    '&:hover': { backgroundColor: 'rgba(0, 243, 255, 0.1)' }
                  }}>
                    {target.name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button onClick={onClose} sx={{ color: 'rgba(255, 255, 255, 0.7)', '&:hover': { color: '#fff' } }}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={!name || isSaving}
          sx={{
            background: 'linear-gradient(45deg, #00f3ff, #ff003c)',
            color: '#fff',
            fontWeight: 'bold',
            '&:hover': {
              boxShadow: '0 0 15px rgba(0, 243, 255, 0.5)',
            },
            '&.Mui-disabled': {
              background: 'rgba(255, 255, 255, 0.1)',
              color: 'rgba(255, 255, 255, 0.3)',
            }
          }}
        >
          {isSaving ? <CircularProgress size={24} sx={{ color: '#fff' }} /> : organization ? 'Update' : 'Create'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
